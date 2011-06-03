
# Filename: Instance.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

import sys, os, string, xml.sax.saxutils, re, time, urllib, copy, threading, imp, shelve
from xml.dom.minidom import parse, parseString
from threading import Event

#this is THE specification for matching Runtime Text Variables [~x~] in XC code.
#in case i wanted to change it during development.
matchTextVar = re.compile('((\[\~)[^\~]+?(\~\]))')
#We need a global lock to all ALL processing during a server reload. The Event() method is
#good for this. Make one, and set/unset it in the Manager.reload() function. Block on it
#in the processXML/processFragment function
globalLock = Event()
globalLock.set()    #start with no blocking, only block (clear()) on reload!

#now that the Instance module has it's singleton, above, matchTextBars, import everything else.
from Utils import DefaultDict, DefaultList, DefaultPathList, DefaultSpacesDict, DefaultTypeDict, StackShell, AutoShell, AttrShell, ArgvShell, DictToObjWrapper, DictToSpaceWrapper
from Utils import dbug_func as dbug
import Internal_Access_Setup, Identity, Manager, Config, Transform, Processor, Parser_Setup, SessionSpace

setup = Config.setup

#configure the storage mechanism (which uses abstraction) for use below.
if setup.dbType.lower() == 'zope32':    from FrozenSpace import Zope32 as DbSource
elif setup.dbType.lower() == 'zodb36':  from FrozenSpace import Zodb36 as DbSource
else:                                   from FrozenSpace import Dummy as DbSource

class Request:
  """One Request per top level request - each sub process gets only it's 
     own context object, through this interface, and shares these. That way
     trackers for unique loading and numbering are consistent across all
     traversals of that particular xml tree."""
     
  #various time saving singletons. fitting.
     
  #since the right fspace adapter is loaded (see above in the module)
  #we can now make the singleton data source all requests will use.
  FSpace = DbSource.New()
     
  #a singleton class to sort, buffer, and manage namespaces used for different xc.
  SessionManager = SessionSpace.New()
  
  #we need to lock individual sessions so that only one is in the system at a time. Not 
  #necessary with zope, but very necessary for xc. Do it here.
  sessionThreads = DefaultTypeDict()
  
  def __init__(self, req, isServer=False, passin={}, extrapath=[]):
    global DefaultDict, DefaultList
    self.startRequestTracker = {}
    self.endRequestTracker = {}
    self.uniqueHeadTracker = {}
    self.insertManager = Processor.InsertTracker()
    self.filterAllTracker = {}
    self.uniqueFilesLoaded = {}
    self.finishHandlers = []
    self.contexts = []
    self.req = req
    self.dom = False
    self.passin = DefaultDict(passin)
    self.isServer = isServer
    self.extrapath = DefaultList(extrapath)
    self.passstack = {}
    self.passstackcounter = 0
    self.switchLaszloForFlash = True
    self.StackShell = StackShell()
    self.autoGenTableABS = {}
    self.all = DefaultSpacesDict()
    self.macroLib = Manager.manager.library.macroLibrary
    self.binary = False
    
  def loadLaszlo(self):
    """special special url '/prefix/_laszlo' gets handling through this function, called via URL after startup
       because everything needs to be ready before this sort of subprocessing happens"""
    #dont refresh laszlo embed tags because it's going to do that anyway
    Manager.manager.reload(self.req, display=False, laszloRefresh=False)
    try:
      #reload the library - extract all type 'laszlo' transforms requested for compile
      #(either ?make=mod.trans or ?makeall=True for every one - a "build world of laszlo swfs" function)
      output = Manager.manager.loadLaszlo(request=self)
    except Exception, msg:
      #turn all laszlo transforms into object tags pointing at an .swf instead of their original transform code.
      #this makes a laszlo transform as the html needed to make the swf - an object tag
      
      #do it here as well as below to let the server recover from a bad compile gracefully. 
      Manager.manager.readyLaszloTransforms()
      raise
    Manager.manager.readyLaszloTransforms()
    return output
    
  def packDB(self):
    """special transform type gets special handling through this function, called via URL after startup
       because everything needs to be ready before this sort of subprocessing happens"""
    #dont refresh laszlo embed tags because it's going to do that anyway
    self.lockThreadForUser(daemon=True)
    self.conn.pack()
    self.unlockThreadForUser(daemon=True)
    return "Pack complete."
      
  def sessionCheck(self):
    """this is a special function called when a session cleanup check is to take place.
       the session check is tendered as a normal request (sans locking, etc) from a thread
       started in SessionManager because the session machinery needs a connection to storage 
       and it's own thread - which is exactly what a request happens to be anyway. can only 
       be issued from localhost, as the first line here enforces."""
    #get the DB connection for this thread.
    self.lockThreadForUser(daemon=True)
    try:
      #call the sessionChecker machinery to see if anything need be done
      self.SessionManager.sessionChecker(self.req)
      output = '<br/>'.join(self.SessionManager.debug)
    except Exception, msg:
      output = 'error: '+str(msg) + "<br/>" + '<br/>'.join(self.SessionManager.debug)
    self.unlockThreadForUser(daemon=True)
    return output
    
  def cleanExit(self):
    """This is a special function that saves all active sessions, then exits. In this fashion,
       when you restart the server, all sessions are available that were running previously."""
    global globalLock
    #stop any other requests from happening.
    globalLock.clear()
    #save all the active namespaces to their file-based sessions.
    self.SessionManager.saveAllSpacesToDB()
    #die now! do not pass go, do not... yeah, Actually this restarts my apache automatically, btw.
    os._exit(1)
      
  def lockThreadForUser(self, daemon=False):
    """This is pretty cool. Start a session, but make requests from one session run in order
       received instead of all at once. activeList is a dictionary of session keys where the
       value is an Event object. The events halt the calling thread until another thread calls
       the events 'set' method when a thread is unlocked in unlockThreadForUser()
       or no entries exist in the queue.
       
       Also makes the connection to the zodb and the session (self.zodb and self.req.acl)"""
    if not daemon:
      #if normal thread block on requests from the same session - linear order.
      activeList = self.sessionThreads[self.req.sessionHandler.sessid]
      if activeList:
        activeList.append(Event())
        activeList[-2].wait()
        del activeList[0]
      else:
        activeList.append(Event())
      #also a normal request gets logged in and it's in-memory session touched
      self.req.sessionHandler.login()
      self.SessionManager.updateLastAccess(self.req.sessionHandler.sessid)    
        
    #Every request has these daemons or not, they are handy. They will always
    #be anonymous since login() wasn't run, above
    
    #get a pointer to the root node in the zodb for this web-site
    self.conn, self.zodb = self.FSpace.connect(app=self.req.app)
    #initialize the ACL connection using the in memory session structure.
    self.req.acl = Identity.IdentityManager(self.req, self.zodb)
        
  def unlockThreadForUser(self, abort=False, daemon=False):
    #if abort flag is true undo the transaction. 
    #!testme
    if not abort: self.conn.commit()
    else:         self.conn.abort()
    #close the connection to the zodb
    self.conn.close()
    if not daemon:
      #close the file db session
      #unlock the next waiting request for this session if waiting:
      self.sessionThreads[self.req.sessionHandler.sessid][0].set()

  def processXML(self, buf, using=[], switchLaszloForFlash=True):
    """
       ** This is the normal API call to activate XC externally.**
      Expects an XML Text Docuement that specifies the modules to be processed in the __uses__
       attribute of the documentRoot node (first opening tag)
       This also has the distinction of being the place where the request level context work is performed,
       Since it is the main gateway to processing. The other functions support internal reprocessing or
       API usage, as the case may be.
    """
    global globalLock   
    #so, if we are re-loading the library, wait until that's done. cool.
    globalLock.wait()
    #if they didn't specifiy the module to use scan the document to see if we even
    #need to process it. a simple approach to a general filter system
    if not using:
      if type(buf) not in (type(u''), type('')): 
        return buf
      if buf[:min(200, len(buf)-1)].find('__uses__') < 0: 
        return buf

    #okay, so there is something to process.
    
    try:    
      #if it's a toplevel request then apply session locking here:
      self.lockThreadForUser()
      #record if we should emit the flash subtransform types instead of their
      #before-compilation forms.
      self.switchLaszloForFlash = switchLaszloForFlash
      #and once we are clear for takeoff, dom the page to be processsed.
      self.dom = parseString(buf)
      
      self_dom = self.dom
      docRoot = self_dom.documentElement
      #firstly, is the flag to use this on? ignore if otherwise. erase attribute if on.
      if not using:
        moduleList = docRoot.getAttribute('__uses__')
        #also nothin to dom:
        if moduleList == '':  
          #unlock this session and start the next if it's outstanding
          self.unlockThreadForUser()
          return buf
        else: 
          #don't want this in the output
          docRoot.removeAttribute('__uses__')
        #get the requested transforms to apply from the moduleList grabbed from the __uses__ attribute
        using = [x.strip() for x in moduleList.split(',') if x]

      #a small concession to convience - if the xml doesn't have a head tag (BLANTANTLY assuming html/xml, for now) make 
      #one. append instead of insert if there are no child nodes of the <html> tag (for a cool tranform action)
      if switchLaszloForFlash and not self_dom.getElementsByTagName('head'):
        docRoot.insertBefore(self_dom.createElement('head'), docRoot.firstChild)
    
      #make a new processor since processing xml is conceptually like processing a request.
      #are we looking for named subblocks (for, say, ZPT integration?)
      if using[0] == '_SCAN':   self.processScannedSubBlocks()
      #or is it just a normal plain jane sorta declared-at-the-top request?
      else:                     self.processXC(using)
      #we need final processing separetely because processXC is recursive in nature.
      #this will do the end blocks and the rest..
      self.finalProcessing()
      output = self.dom.toxml()
      #remove the doctype statement. Minidom headaches. This SHOULD be to only remove it if the return isn't a top-level call. Lucky, that's what
      #ProcessXML is used for. Use processFragment() if you want to sub evaluate xml "on the side" or for (server calls)
      try:  output = output[min(output.index('?>')+2, 60):]
      except: pass
      #unlock this session and start the next if it's outstanding.
      self.unlockThreadForUser()
      if self.binary: return self.binary
      else:           return output
    except:
      #if there was a boo-boo (often from client code, even!), cool, but unlock this session.
      self.unlockThreadForUser(abort=True)
      raise
    
  def applyXC(self, modsToUse, body, **kwargs):
    """This handy little thing will take a string and pass it through the system as if it were a server call."""
    if modsToUse:
      self.passin=kwargs
      return self.processFragment(body, modsToUse, topmost=True)
    else:
      return Request(self.req, isServer=True).processXML(body)
    

  def processFragment(self, buf, using, scansingle=False, backendFiltering=True, saveas=False, topmost=False, switchLaszloForFlash=True, dbg=False, lastauto=False):
    """Expects a XML Text fragment that has elements to be processed by the 
       modules in the list 'using' (required)
    """
    
    global globalLock
    #so, if we are re-loading the library, wait until that's done. cool.
    globalLock.wait()
    try:
      #You see, servers call processFragment directly (since a server is a 'fragment')
      #These types of calls need extra setup then the normal recursive calls processFragment
      #gets from the other parts of the engine. So, if it's not "topmost" (never if not server btw)
      #then we can just skip some of the init sauce that makes this function uglier then otherwise :) 
      if topmost:
        self.lockThreadForUser()
        self.switchLaszloForFlash = switchLaszloForFlash
        
      buf = '<null>%s</null>'%buf
      try:  
        chunk = parseString(buf)
      except Exception, msg:
        self.conn.close()
        raise Exception, xml.sax.saxutils.escape(str(msg)) +"\n\nFrom a server or define call...\n\n"+xml.sax.saxutils.escape(`buf`)
      if not self.dom:
        self.dom = chunk
      #reuse the existing context since fragments are called as part of a larger request, by
      #defintion - we want to use that requests' info, not overwrite it.
      self.processXC(using, chunk=chunk.documentElement, scansingle=scansingle, saveas=saveas, backendFiltering=backendFiltering)
      #if we are making a laszlo app - it's always served via processFragment() so do the end processing.. "normal" processing
      #has this done up in processXML()
      if not switchLaszloForFlash: self.finalProcessing()
      #if dbg: raise 'made it past?'
      output ='\n'.join([x.toxml() for x in chunk.firstChild.childNodes])
    
      #unlock this session and start the next if it's outstanding
      if topmost: 
        self.unlockThreadForUser()
      if self.binary: return self.binary
      else:           return output
    except:
      if topmost:
        self.unlockThreadForUser(abort=True)
      raise

  def processScannedSubBlocks(self):
    """Given a top level processor previously instantiated, a dom, and the plain request object, 
       search it's tree for XC subblocks, each of which is treated with separately specified
       modules via the __uses__ attribute assigned to each one."""
    #horrible! but have to: the XC nodes need to be visited in depth first reverse,
    #so this determines that from the DOM's parentNode method, the more times we can go up, 
    #the deeper it is in the tree. sort on that, and there you go
    buf = [x for x in self.dom.getElementsByTagName('xc')]
    blocksToProcess = []
    blocksToProcess_append = blocksToProcess.append
    for node in buf:
      at, nlev = node.parentNode, 0
      while at:
        at = at.parentNode
        nlev += 1
      blocksToProcess_append([nlev,[node]])
    blocksToProcess.sort()
    blocksToProcess.reverse()

    #normal scan run for transform directives in the xml
    for block in blocksToProcess:
      element = block[1][0]
      element_parentNode = element.parentNode
      element_parentNode_insertBefore = element_parentNode.insertBefore
      #if they are scanning - flip out the applied modules per base XC tag, as specified
      #each transform element
      moduleList = element.getAttribute('__uses__')
      if moduleList == '':  continue
      else:         element.removeAttribute('__uses__')
      #get the requested transforms to apply from the moduleList grabbed from the __uses__ attribute
      usingForThisBlock = [x.strip() for x in moduleList.split(',')]
      self.processXC(usingForThisBlock, chunk=element)
      #now take the results of that process and put it in place of the original XC tag:
      [element_parentNode_insertBefore(x.cloneNode(deep=True), element) for x in element.childNodes]
      element_parentNode.removeChild(element).unlink()

  def processXC(self, using, chunk=False, scansingle=False, saveas=False, backendFiltering=False):
    """THE workhorse loop of the XC system, this scans a dom instance for those transforms thus supplied.
       Every node that is of a type addressed by transforms will be visited to determine if action is needed.
       Behavior in this function affects the order nodes are visited, transform types to be filtered, etc.

       chunk      = chunk of xml to process on, which is read out (.toxml()) after transformation by the calling function
       modulelist   = those XC modules to be considered, 
       req        = the current request from mod_python
       scansingle   = if true, a string with the name of a single transform to apply to the DOM regardless of other settings
       backendFiltering = if true, will look to process transforms not advertised to the client, eg, the define transform type.
    """
    #see we need depth first no matter the order the modules called. so scan in the loop and use
    #partsToProcess to hold the tag/trans combinations that will then be visited in the desired order.
    if not chunk: chunk = self.dom
    self_dom = self.dom
    toBeProcessed = []
    Manager_manager_library = Manager.manager.library
    using = dict([(x, True) for x in using]).keys()
    for modname, module in [(str(x), Manager_manager_library.getModuleByName(str(x))) for x in using]:
      #if there is a start transform, run it.
      #if we are processing the main DOM, perform the start of request operations specified by the start request transform, if available
      
      if not self.isServer:
        if not self.startRequestTracker.has_key(modname):
          for includedMod in Manager_manager_library.macrosLoadedPerModule[modname]: 
            if not self.startRequestTracker.has_key(includedMod):
              self.startRequestTracker[includedMod] = True #do this first to prevent recursion!
              thismod = Manager_manager_library.raw[includedMod]
              if thismod.has_key('._STARTREQ'):
                Context(req=self, mod=includedMod, saveas=saveas, trans=thismod['._STARTREQ']).applyTransformTo(self_dom.documentElement.firstChild)
          
        if not self.endRequestTracker.has_key(modname): 
          for includedMod in Manager_manager_library.macrosLoadedPerModule[modname]: 
            if not self.endRequestTracker.has_key(includedMod):
              self.endRequestTracker[includedMod] = True #do this first to prevent recursion!
              thismod = Manager_manager_library.raw[includedMod]
              if thismod.has_key('._ENDREQ'): 
                self.finishHandlers.append(thismod['._ENDREQ'])
            
      if scansingle:
        #Just select one transform to run (think server transforms where only one transform is generated.)
        transToScan = module[scansingle]
        globalsToScan = {} 
        tagsToScan = {transToScan.tag:True}
        transNames = {unicode(transToScan.attrname):True}
        transMap = {unicode(transToScan.name):transToScan}
      else:
        #only process the formal transform types like 'filter' or 'filterall' that advertise a presence to the 
        #client. Other transform types are only used in constructing the library support, so to speak,
        #that support these 'first-class' transforms.
        if backendFiltering:
          globalsToScan, tagsToScan, transNames, transMap =\
            Manager_manager_library.scanningDataAllCaught[str(modname)]
        else:
          globalsToScan, tagsToScan, transNames, transMap =\
            Manager_manager_library.scanningDataNormalCaught[str(modname)]

      #find the filterall triggered nodes, if any. "filter (tag)" applies to global (topmost) dom node, which is why it's separate.
      if not scansingle:
        for key in globalsToScan.keys():
          if not self.filterAllTracker.has_key(key):
            trans = globalsToScan[key]
            for tag in self_dom.getElementsByTagName(trans.tag):
              toBeProcessed.append((tag, trans))
            self.filterAllTracker[key] = True
      
      #for each type of unique tag asked for in the module, look at each and see if
      #any attribute matches a transform defined by this module. Faster then previous method..
      try:
        for tagtype in tagsToScan.keys():
          for tag in chunk.getElementsByTagName(tagtype):
            for attr in tag.attributes.keys():
              if transNames.has_key(attr):
                mod, name = attr.split('.')
                toBeProcessed.append((tag, transMap["%s.%s.%s"%(mod, tag.tagName, name)]))
                #why break? because XC calls' ordering matters and thus more then one is unpredictable?
                #maybe we change this - it wasn't like this to begin with.., but it doesn't seem to be needed!
                break
      except:
        msg = "Could not find the transform %s.%s.%s which was requested in: %s." % (mod, tag.tagName, name, modname)
        raise msg.encode('utf-8')
    
    #take the resulting tag/trans pair and sort them by NODE DEPTH and trans name:
    #we end up with all the operations per-recursion minimized with respect to order
    #since they are ordered one after another going shallower, a result of the call above.
    partsToProcess = []
    partsToProcess_append = partsToProcess.append
    for pair in toBeProcessed:
      elem, nlev = pair[0], 0
      at = elem.parentNode
      #to find depth climb up and count on the way - depth reverse listing (you know a better way?)
      while at:
        at = at.parentNode
        nlev += 1
      partsToProcess_append((nlev,pair))
    partsToProcess.sort()
    partsToProcess.reverse()

    #AND FINALLY, apply the transforms to those nodes, such that
    #we respect the processing order we determined above (depth-first-reverse)
    for entry in partsToProcess:
      node, currtrans = entry[1][0], entry[1][1]
      #that good ol' processing magic thanks to the Context object..
      Context(req=self, mod=currtrans.modulename, saveas=saveas, trans=currtrans).applyTransformTo(node)
      #if it's the special tag 'fragment' (the only special tag other then the 'XC' tag)
      #then instead of returning the now processed tag, insert it's inside nodes into the dom tree
      #where the original node would have been.
      if currtrans.tag == 'fragment':
        node_parentNode = node.parentNode
        [node_parentNode.insertBefore(x.cloneNode(deep=True), node) for x in node.childNodes]
        node_parentNode.removeChild(node).unlink()
    return chunk

  def finalProcessing(self):
    #two things to do during final processing. Perform all 'finish' transforms -- if a module
    #has one. Any action that needs full access to the DOM gets it here, except for transforms
    #that do so on their own dime (with their own dom-access capabilities, which may or may not
    #be able to write at this level, depending on the context in which they are invoked. Things
    #usually flow down-scope-only in transforms' logic, but sometimes not. Extra power.)
    if not self.switchLaszloForFlash: endNode = self.dom.documentElement.firstChild
    else:                             endNode = self.dom.documentElement
    for trans in self.finishHandlers:
      if len(trans.rules) > 1 or trans.rules[0][0] != 'pass':
        Context(req=self, mod=trans.modulename, trans=trans).applyTransformTo(endNode)

######## Almighty Context, one made per run, has a Processor() assigned to it, one per context. #################### # # #  #   #  #

#WARNING, this code uses x_y instead of x.y to save time on assignment where possible. they
#are equivenlent.
class Context:
  #these are singletons for all contexts. it's a namespace that provides transparent 
  #access to an underlying postgres database. various subpaths of this become the 
  #various spaces written to as transforms carry out their duties.
  
  #elevated access list
  IAS_access = Internal_Access_Setup.permissions
  
  #the means to recognize an instance name on a XC call.
  matchSaveName = re.compile( "^\[\w+\]\:" )
  
  #shorthand for lateragin'
  esc = xml.sax.saxutils.escape
  unesc = xml.sax.saxutils.unescape
  quote = urllib.quote
  unquote = urllib.unquote
  
  def __init__(self, req=None, mod=None, trans=None, saveas=False, dbg=False):  
    #the request is the top level object spooling off these contexts.
    #having the request pointer around lets us maintain a single place
    #for managing data that becomes unique for each transform performed.
    #This, then, could be the equiv. of 'self' in a python class. Lives
    #across the life time o of a transform call, which would be proportionally
    #longer the more XC calls it fires off from inside itself. fyi :)
    self.request = req
    self.saveas = saveas
    self.wrapstate = []
    self.wrapsadded = []
    self.modulesToUse = []
    #prepare the context for use as specified in the params
    self.perModule(mod)
    self.perTransform(trans)
    #attach a processor to this context.
    self.Proc = Processor.Process(req=self.request, context=self)
    
  def applyTransformTo(self, tag):
    self.perTag(tag)
    self.Proc.applyTransformTo(tag)
    self.request.StackShell.remove()
    
  def perModule(self, modulename):
    global setup, ObjectDict, Manager
    #Key a new namespace to the user and module being executed. These spaces are supposed to die with the session...
    self_request = self.request
    self_request_req = self_request.req 
    self.space = self_request.SessionManager.getSpaceFor(self_request.req.acl, modulename)
    self_space = self.space
    currReq = getattr(self_space, 'REQ', False)
    
    #The injected attributes at the transform level of the XC system.
    #DON'T do 'em if the space has been initialized already!
    #! THESE BETTER NOT CHANGE OVER THE LIFE OF THE ENGINE
    if not currReq:
      #this will take a list of modules to use and an xml snippet to process, returning
      #the result as a string. You can use this in python blocks in transforms to further
      #programattically invoke other transforms. extremely useful!
      self_space.applyXC = self_request.applyXC
      #a pointer to itself for use in setattr statements, etc.
      self_space.SPACE = self_space
      #points to the config values set from the XC/setup plist
      self_space.CONF = setup
      #this takes a snippet of xml and returns a nodelist. 
      self_space.PARSE = self.node
      #escapes/unescapes a sequence for sending to xml
      self_space.ESC = self.esc
      self_space.UNESC = self.unesc
      #quote/unquote a sequence for sending over query string
      self_space.QUOTE = self.quote
      self_space.UNQUOTE = self.unquote
      #the current module name, which doesn't change over repeated calls, of course.
      self_space.MOD = modulename
      #These point to the FS path of both the transform directory and the specific 
      #module's path for quick access.
      self_space.BASEPATH = setup.basePath
      self_space.THISPATH = "%s%s/"%(setup.basePath,modulename)
      #These point to the url of the XC install and the current module, sans the http://xxx.com part
      self_space.BASEURLREL = setup.serverPath
      self_space.THISURLREL = "%s%s/"%(setup.serverPath,modulename)
      #these point to the full url for the XC installation and the url specific to this module as well.
      self_space.BASEURL = setup.serverUrl
      self_space.THISURL = "%s%s/"%(setup.serverUrl,modulename)
      #will store all the 'self' namespaces for all instances of transforms.
      #It can thus easily be saved when then session is unloaded to zodb.
      self_space.SELFS = {}
      #take this out perhaps, after debugging and everything..
      self_space.ADMIN = self
            
      #HERE!, if we are here in this block, it means this is a fresh session. So, load an old session in from the
      #Zodb IF THERE IS ONE. We do this here, because the above attriubtes should already be available (for init blocks)
      #when the old session is reloaded. This is the right place. (init blocks shouldn't use context stuff, below,
      #although a function defintion can, since by the time it's called it will be in the namespace...)
      self_request.SessionManager.loadSpaceFromDB(self_request.req.acl, modulename)
            
    #don't do these if the request is the same as last time; once per request.
    #! THESE WILL CHANGE *ONCE* PER REQUEST
    if self_request_req != currReq:
      #the following are new each time around as opposed to the static stuff, above.
      self_space.REQ = self_request_req
      self_space.MACROS = self_request.macroLib
      self_space.ARGS = self_request.req.args
      self_space.ARGP = DefaultPathList([x for x in self_request.extrapath if x])
      self_space.PASSED = self_request.passin
      
      #initialize the inter-module connector (allows python namespace "bridging", mostly (initially)
      #useful for certain macro patterns)
      self_space.ALL = self_request.all
    
      #HERE ARE THE FROZENSPACE ATTRIBUTES FOR PERSISTENCE. updated once per request, so's the app is mighty fresh.'.
      self_space.ROOT = self_request.zodb
      self_space.GLOBAL = self_request.zodb['global'][modulename]
      self_space.LOCAL = self_request.zodb['local'][modulename][self_request_req.acl.user]
      self_space.USER = self_request.zodb['user'][self_request_req.acl.sessid]
    
  def perTransform(self, trans):
    pass #dbug("in trans:"+trans.name)
    self.trans = trans
    self_trans = self.trans
    self_request_req = self.request.req
    
    #HERE is where we handle security concerns. IF this current user isn't authorized to
    #view this transform, set it's associated denied block as the transform to run instead.
    if self_trans.authorized:
      if not self_request_req.acl.isInGroup(self_trans.authorized):
        if self_trans.deniedHandler.rules:
          self.trans = self.trans.deniedHandler
          #raise `self.trans.rules`
        else:
          raise Exception, "Access denied for transform %s"%self.trans.name
       
    #if it's a laszlo type transform, substitute it's laszloHandler xml (object/embed flash) 
    #transform for the type that is held in the library that turns into the source file.
    if self_trans.kind.startswith('laszlo'):
      if self.request.switchLaszloForFlash:
        self.trans = self_trans.laszloHandler
          
    #Run the init block for this transform in the current namespace if it hasn't been done.
    #Record it in the namespace's INITSPACETRACKER to ensure that. This ALSO has the advantage of saving
    #the transforms that have an init block run, so that we can re-run them on session reload!
    initspaceTracker = self.space.INITSPACETRACKER
    if not initspaceTracker.has_key(self_trans.trigger_attr):
      pass #dbug("INITING: " + self.space.REQ.session.id+self_trans.name + " with " + `dir(trans)`)
      if self_trans.initspaceHandler.rules[0][2]:
        exec self_trans.initspaceHandler.rules[0][2] in self.space.__dict__
        pass #dbug(self_trans.initspaceHandler.rules[0][2])
      initspaceTracker[self_trans.trigger_attr] = True 
      
    #?NOTE: these CAN CAN change during the course of a request, so by updating per-transform, it will be synced with reality!
    #?this caused no small heartache when testing finish transforms ;(
    #! THESE CHANGE EVERY TRANSFORM CALL
    self.space.DOM = self.request.dom
    self.space.DOC = self.request.dom.documentElement
      
    #This frozen space is for the transform, so it's calculated here.
    self.space.TRANS = self.request.zodb['trans'][self_trans.modulename][self_trans.atomicname][self_request_req.acl.user]
    #this can get changed during a request?
    
    #synthesize some constants for later, like fullname, the mod.trans form of the name.
    #if the trigger attr is "" (aka a global transform) then the fullname is mod_tagtype.
    if self_trans.trigger_attr != '': self.fullname = self_trans.name
    else:                             self.fullname = '%s_%s'%(self_trans.modulename,self_trans.tag)
    self.fullname.replace('.','_')
    self.lastSeenTag = -1
    return self
    
  def perTag(self, tag):
    self.tag = tag
    self_trans = self.trans
    self_request_req = self.request.req
    self_space = self.space
    
    #perform the logic that allows the saveas attribute to "inherit" from a calling node: if saveas isn't provided
    #but the calling context has saveas, then use that. By this point it will already have that name, if provided, 
    #which is why if self.saveas is false, we set it to 'all' which is where unnamed transform data lives.
    try:
      savename = tag.getAttribute(self_trans.attrname)
    except:
      raise self_trans.name
    match = self.matchSaveName.search(savename)
    if match == None:
      if not self.saveas: self.saveas = 'all'
    else:
      span = match.span()
      self.saveas = savename[1:span[1]-2]
      tag.setAttribute(self_trans.attrname, savename[span[1]:])
    
    self.uid = '%s_%s'%(self.trans.scoredname, self.saveas)
    
    autoGenTable = self_space.AUTOGENTABLE
    autoGenTableABS = self.request.autoGenTableABS
    try:    autoGenTable[self_trans.name] += 1
    except: autoGenTable[self_trans.name] = 0
    runnum = autoGenTable[self_trans.name]
    try:    autoGenTableABS[self_trans.name] += 1
    except: autoGenTableABS[self_trans.name] = 0
    reqrunnum = autoGenTableABS[self_trans.name]
    self.uidAndNum = str("%s%s"%(self.uid,runnum)).replace('.', '_')
    
    pass #dbug("in apply:"+self_trans.name + ' name is ' + self.saveas + ' saveas attr is: [' + self.tag.getAttribute('saveas') + ']')
    
    #! THESE CHANGE EVERY TIME A TAG IS EVALUATED
    if not self_space.SELFS.has_key(self.uid):
      self_space.SELFS[self.uid] = DictToObjWrapper({})
  
    StackShell = self.request.StackShell
    #This is the autonumbering code! this in it's simple self is the heart of self-referential javascript
    StackShell.add(
      {
        'NUM':str(runnum), 
        'REQNUM': str(reqrunnum),
        'NAME': self_trans.atomicname,
        'AUTO':AutoShell(self.uidAndNum).prepare(StackShell),
        'TAG':self.tag, 
        'INST':self.saveas,
        'ARGV':ArgvShell(self.tag.getAttribute(self_trans.attrname)).using(self.request.passstack),
        'ATTR':AttrShell(self.tag),
        'HERE':self.request.zodb['here'][self_trans.atomicname][self_request_req.acl.user][self.saveas],
        'self':DictToObjWrapper(self_space.SELFS[self.uid])
      }
    )
      
    #copy 'em into the transform namespace for quick use.
    #also call to reinitialze environment on return from subcall
    self.setSpaceForTag()
    #if there is a default block, take what isn't passed as an argument and fill it in
    #before executing..
    if self_trans.defaultHandler.rules[0][2]:
      defaults = self_trans.defaultHandler.rules[0][2]
      passed = StackShell.get('ARGV', -1)
      passedin = passed.keys()
      for key in defaults.keys():
        if key not in passedin:
          passed[key] = defaults[key]
    
    #zero out the various state trackers used as the transform rules are evaluated.
    self.modulesToUse = []
    self.loopstate = []
    self.loopindexes = []
    self.abandonedTags = []
    self.lastConditionState = []
    self.currRule = None
    self._i = 0
    return self
    
  def setSpaceForTag(self):
    """On the first run of a transform or if another transform in the same module has been called, 
       (which dirties injected namespace variable) we'll need to 'refresh' the namespace 
       before return. that's what this does.
    """
    self_space = self.space
    StackShell = self.request.StackShell
    [setattr(self_space, x, StackShell.get(x, -1)) for x in StackShell.keys()]
    
  def node(self, text):
    """a quick way to make a DOM tree for xml - just exposes parseString, really, if a transform wants to use it."""
    return parseString(text).documentElement
    
