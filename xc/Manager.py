
# Filename: Manager.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#this module just holds all the parsed modules'
#transforms, and manages reloading them if needed.
#it actually recieves the raw transform defintions,
#so finessing things like determining which aliases 
#hold which transforms is also handled here.

import sys, string, os, traceback, copy, threading, urllib, xml.sax.saxutils, re
import cPickle as pickle
from xml.dom.minidom import parse, parseString
import Parser, Server, Instance, Utils, Parser_Setup, Config, Transform
from Utils import dbug_func as dbug
from popen2 import Popen3
import Utils

setup = Config.setup

######## see bottom for singleton module objects #################### # # #  #   #  #
    
class Manager:
  #since the manager class does post-compilation steps it'll need this for laszlo later..
  laszloEmbedRules =\
    [ ['prepend', ['width'], "[~ARGV['width']~]"], 
      ['prepend', ['height'], "[~ARGV['height']~]"], 
      ['addxml', [], '<param name="movie" value="[[name]].swf">\n <embed src="[~THISURL~][[name]].swf" width="[~ARGV[\'width\']~]" height="[~ARGV[\'height\']~]"/>\n</param>'], 
      ['remove', [], '[[mod]].[[name]]']]
  
  def __init__(self, frompickle=False):
    """Make a new manager, to be filled with a library object."""
    self.esc = xml.sax.saxutils.escape
    self.library = None
    self.server = None
    self.preCompiles = {}
    self.loadAll()
    self.readyLaszloTransforms()
    
  def loadAll(self, export=False):
    """Reload all of the transforms from the transform directory. There isn't support for just
       one module, as it stands.. which is for the better considering the inheritence, precompiing
       and other relational junk that goes on.. doesn't seem to take that long currently anyway."""
    
    #pass the moduleList (parser objects) to the library function to be post processed, collated, and organized
    #load from previously saved pickle file? cool!
    if setup.usePickle.lower() == 'true':
      sys.stderr.write("Loading compiled XC library...")
      self.library = pickle.load(open(setup.TransformsPicklePath))
    else:
      sys.stderr.write("Loading XC library from source...")
      #load the transforms directory into parser objects
      moduleList = [(x, setup.basePath) for x in os.listdir(setup.basePath) if not ['.','_'].count(x[0])]
      #and also load the modules in the zopepath into parser objects (if available - neat that it works this way
      #moduleList += [(x, setup.zopePath) for x in os.listdir(setup.zopePath) if not ['.','_'].count(x[0])]`
      self.library = ModuleLibrary(moduleList=moduleList)
      if export:
        pickle.dump(self.library, open(setup.TransformsPicklePath, 'w'))
        
    #now that the library is loaded (and pickled - can't pickle code objects, fyi!), search for and 
    #precompile (yeah!) all expressions into a singleton dictionary residing in the library class that will 
    #be used for real-time lookup in the processor module during var replacements detected during those transform 
    #calls. cool! Also compile python blocks and leave them in place. Same for initspaceHandler and defaultHandler subtransforms..
    
    #also, to stay econmoical, also grab all transform types that have 'laszlo' in the name will be collected for 
    #additional post processing.
    self.preCompiles = {}
    for mod in self.library.raw.keys():
      for trans in self.library.raw[mod]:
        self.library.preCompile(self.library.raw[mod][trans], self.preCompiles)

    #using the now fully prepared library object, initialize and make available the singleton ServerRoot, which dispatches
    #calls to the XC subsystem (the majority of 'em usually) as opposed to the outbound filtration concept.
    self.server = Server.ServerRoot(self.library)
    sys.stderr.write("Loading complete.\n")
    return self
    
  def loadOne(self, modname, textbuf):
    lib = ModuleLibrary(moduleList=moduleList)
        
  def reload(self, req, display=True, laszloRefresh=True):
    #pretty display.. oooh. (actually - this will be interface to some error checking, too but lists good info if successful)
    #Lock all threads until reload complete
    Instance.globalLock.clear()
    try:
      #this is the adapted request object, not an instance of the Request class, so make the dict we want
      if req.args.has_key('export'):  self.loadAll(export=True)
      else:                           self.loadAll()
      if laszloRefresh:              
        self.readyLaszloTransforms()
      
      if not display: 
        Instance.globalLock.set()
        return
      
      rowColors = ['#DCECE4', '#BCCCC4', '#030303']
      output = """<html><body style="background: #aaaaaa; font-family: arial;">
            <div style="padding: 15px; font-family: arial;">
            XC version 0.7.0 Copyright James Robey, 2005-2006<br/>
            Module Backend/Debugging Console.<br/><br/>
            <b>If you see this, XC started successfully.</b> Loaded transforms are provided for reference.<br/><br/>
            <table style="width:100%;">
            <tr style="background: #DCECE4; text-align: center;">
            <td width="10%">
            <b>Modules Loaded:<b><br/>
            </td>
            <td width="20%"><b>name</b></td>
            <td><b>kind</b></td>
            <td><b>comment</b></td>
            </tr>"""
            
      closeoutput = """</body></html>"""
  
      raw = self.library.raw
      modlist = raw.keys()
      modlist.sort()
      genout = []
      for module in modlist:
        genout.append("""<tr style="color: white; background: %s;"><td style="text-align: center;">%s</td></tr>""" % (rowColors[2], module))
        k = [(raw[module][x].kind, x) for x in raw[module].keys() if 'req' not in raw[module][x].kind]
        k.sort()
        for i, trans in enumerate([x[1] for x in k]):
          kind = raw[module][trans].kind
          textclr = '#000000'
          if 'define' in kind: textclr = '#888888'
          genout.append("""<tr style="color: %s; background: %s;"><td></td><td>%s</td><td>%s</td><td style="font-size: 0.8em;"><div style="padding: 5px;"><pre>%s</pre></div></td></tr>"""\
                 % (textclr,
                  rowColors[i%2], 
                  raw[module][trans].name, 
                  raw[module][trans].kind,
                  raw[module][trans].documentHandler.rules[0][2].replace('\n', '<br/>')))
      genout.append("""</table></div>""")
      output = "%s%s%s" % (output, ''.join(genout), closeoutput)
    except:
      Instance.globalLock.set()
      raise
    Instance.globalLock.set()
    return output
    
  def readyLaszloTransforms(self):
    #?Bread and butter to change laszlo transforms into runnable html callable tranforms   
    for transform in self.library.getAllTransformsByKind('laszlo'):
      #replace the transform with the launch code (manually!):
      mod = transform.modulename
      name = transform.atomicname
      embedRules = []
      for rule in self.laszloEmbedRules:
        newrule = copy.deepcopy(rule)
        newrule[2] = newrule[2].replace('[[name]]', name)
        newrule[2] = newrule[2].replace('[[mod]]', mod)
        embedRules.append(newrule) 

      transform.laszloHandler = copy.deepcopy(transform)
      transform.laszloHandler.rules = embedRules
      #compile the new rules before assigning "finished" handlers that don't like
      #to be preCompiled twice ;)
      self.library.preCompile(transform.laszloHandler, self.preCompiles)
      transform.laszloHandler.defaultHandler.rules[0][2] = {"width":500, "height":500}
      for x in transform.defaultHandler.rules[0][2].keys():
        transform.laszloHandler.defaultHandler.rules[0][2][x] = transform.defaultHandler.rules[0][2][x]
        
  def loadLaszlo(self, request=False, refreshOnly=False):
    """- special transform type gets special handling through this function, called via URL after startup
         because everything needs to be ready before this sort of subprocessing happens.
       - If refreshonly we aren't recompiling the XC in question (so we don't need a request), we're just
         computing the embed tag which got wiped out on reload.."""
    lib = self.library.raw
    output = ""
    #either process a single transform or loop through and compile them all.
    toscan = []
    processed = []
    #? REMEMBER, this gets run to compile, but the code after this block still needs to run at server start.
    if request.req.args.has_key('make'):
      mod, trans = request.req.args['make'].split('.')
      try:    toscan.append(lib[mod]['object.%s'%(trans)])
      except: raise 'the transform %s.object.%s not found.'%(mod, trans)
    elif request.req.args.has_key('makeall'):
      toscan = self.library.getAllTransformsByKind('laszlo')
    else:
      raise "Provide either ?make=mod.trans or ?makeall=true to proceed with compilation."
    for transform in toscan:
      processed.append(transform.name)
      mod = transform.modulename
      name = transform.atomicname
      pathprefix = "_lzx"
      basepath = "%s%s/%s"%(setup.basePath, mod, pathprefix)
      filepath = "%s%s/%s/%s.lzx"%(setup.basePath, mod, pathprefix, name)
      swfpath = "%s%s/%s/%s.swf"%(setup.basePath, mod, pathprefix, name)
      swffinalpath = "%s%s/%s.swf"%(setup.basePath, mod, name)

      #make the dir if it doesn't exist
      try:  os.makedir(basepath)
      except: pass

      #build the file and place it at 
      starttag = """<object %s.%s="true"/>"""%(mod,name)
      output = request.processFragment(starttag, [mod], topmost=True, switchLaszloForFlash=False)
      try:    chunk = parseString(output)
      except: raise "Error in top level output from laszlo app, %s, %s"%(lib[trans].name, str(output))
      chunk.documentElement.tagName = 'canvas'
      chunk.documentElement.setAttribute('proxied', 'false')
      #write out to file, changing the root tag to canvas instead of object (nice little feature)
      fp = open(filepath, 'w')
      fp.write(chunk.documentElement.toxml())
      fp.close()

      #build the command and run it, producing an .swf
      compileLaszloCommand = """%s;%s %s"""%(setup.javaEnvironment, setup.lzcPath, filepath)
      try:
        run = Popen3(compileLaszloCommand, capturestderr=True)
        run.wait()
        output = run.fromchild.read()
        if output: raise Exception, output
        else: os.rename(swfpath,swffinalpath)
      except Exception, msg:
        #if there is a an error in compiling the laszlo app, produce a nice and helpful error display,
        #showing the problematic line and index into that line:
        output = []
        where = str(msg).split(':')[1:]
        
        try:
          name, line, character = where[0][1:], int(where[1]), int(where[2])
        except:
          raise """\
An error occured while moving the result swf file to the parent folder:

Path:
%s

Error:
%s

output swf file:
%s

swf should be copy to parent and renamed:
%s
------
"""%(compileLaszloCommand, msg, swfpath, swffinalpath)
        
        if os.path.exists(filepath):
          linetext = open(filepath).readlines()[line-1]          
          output = 'Line %s, Character %s, Error: %s\n'%(line, character, str(msg))
          codedump, i, wrapbuf = list(output), 0, 0
          for i, entry in enumerate(linetext):
            if i == character-1:
              codedump.append('\n\n############ Line %s, Char %s... '%(line,character))
            if entry == '\n': 
              codedump.append(entry)
              wrapbuf = 0
              continue
            elif wrapbuf % 80 == 79: 
              codedump.append('\n')
            codedump.append(entry)
            wrapbuf += 1
          raise '\n'.join([self.esc(x) for x in ''.join(codedump).split('\n')])
        else:
          raise "Error compiling lzx (no output was generated)"
              
    if not output: output = "Load OK: %s"%(processed)
    return "Laszlo Transform (re)loaded: "+output
  
  
class ModuleLibrary:
  evalsym = re.compile('((\[\~)[^\~]+?(\~\]))')
  def __init__(self, moduleList=None, export=False):
    #)IDEA IS: TAKE A BUNCH OF TRANSFORM OBJECTS AND REORGANIZE THEM INTO A USEFUL LIBRARY STRUCTURE.
    
    #take the specified transform modules and parse them into the transform dict. and other data structures;
    #the final product of a load. Why the *final* product? because things like the 'alias' transform type is
    #calculate at compile time, after load, for instance.. so are before and after clauses.   
    
    #Before we load the transforms again, wipe out the Skins global so that skins will be reloaded.
    #!consider this a temporary fix for when active reloading sensing in is place.
    Parser.Skins = {}
    transformLibrary = [Parser.TransformsParser(sourceFile=x, basepath=y) for x,y in moduleList]
    errors = Parser.TransformsParser.collectedErrors
    if errors:
      #clear the errors for next run - a singleton records all Parser instances so it's not
      #something that goes away with the class's run, but can be reported all at once.'
      msg = "Parser Errors:<br/><br/>"+"<br/><br/>".join(errors)
      Parser.TransformsParser.collectedErrors = []
      raise Exception, str(msg)
      
    self.Skins = Parser.Skins
    self.raw = {}
    self.scanningDataNormalCaught = {}
    self.scanningDataAllCaught = {}
    self.macrosLoadedPerModule = {}
    toInherit = []
    
    #)get a pointer to the singleton macroLibrary in the parser object
    self.macroLibrary = transformLibrary[0].macroLibrary
    
    #)reorganize the modules into a dictionary of form library[MOD_NAME][TRANSFORM_NAME]
    #which is mighty useful all over the place, later on.
    for module in transformLibrary:
      #?take and unify all the macro files loaded for each module. 
      #?once per load, a module will be loaded into the start transform
      #raise `module.macrosLoaded.keys()`
      self.macrosLoadedPerModule[module.modulename] = module.AllMacrosLoaded
      for trans in module.listOfAllTransforms():        
        if not self.raw.has_key(trans.modulename):
          self.raw[trans.modulename] = {}
        self.raw[trans.modulename][trans.trigger_attr] = trans
        #save all the inherited transforms to be processed by calculateInheritedTransforms()
        if trans.inheritFrom:
          toInherit.append(trans)
      
    #)Now we calculate all of the inheritance transforms -- they are not initialized until after compile time
    #because any module may inherit from any other module.
    self.calculateInheritedTransforms(toInherit)
    
    #)prepare the data that will let us find matching nodes given a array (called a 'module') with transforms.
    #that is, a dict of globals, tagtypes, attribute_triggers, and fullname -> transform mapping (in transMap)
    for mod in self.raw.keys():
      #?look at each transform, get the normally caught transforms ('public' ones, if you will)
      transToScan = [self.raw[mod][x] for x in self.raw[mod].keys() if self.raw[mod][x].kind in Parser_Setup.normalCaughtTransforms]
      globalsToScan, tagsToScan, transNames, transMap = {}, {}, {}, {}
      for trans in transToScan:
        if trans.atomicname == '':
          globalsToScan[trans.name] = trans
        tagsToScan[trans.tag] = True
        transNames[unicode(trans.attrname)] = True
        transMap[unicode(trans.name)] = trans
      self.scanningDataNormalCaught[mod] = (globalsToScan, tagsToScan, transNames, transMap)
        
      #)look at each transform, get all caught transforms ('internal' ones, if you will)
      transToScan = [self.raw[mod][x] for x in self.raw[mod].keys() if self.raw[mod][x].kind in Parser_Setup.allCaughtTransforms]
      globalsToScan, tagsToScan, transNames, transMap = {}, {}, {}, {}
      for trans in transToScan:
        if trans.atomicname == '':
          globalsToScan[trans.name] = trans
        tagsToScan[trans.tag] = True
        transNames[unicode(trans.attrname)] = True
        transMap[unicode(trans.name)] = trans
      self.scanningDataAllCaught[mod] = (globalsToScan, tagsToScan, transNames, transMap)
    
  def getScanningInfo(self, module):
    return self.scanning[module]
    
  def getTransform(self, module, name): 
    return self.raw[module][name]
    
  def getModuleNames(self):
    return self.raw.keys()  
    
  def getModuleByName(self, name):  
    try:    mod = self.raw[name]
    except: raise "Could find requested module:" + `name`
    return mod
    
  def getModulesByName(self, names):  
    try:    mods = [self.raw[x] for x in names]
    except: raise "Could find requested modules:" + `names`
    return mods
    
  def getAllTransformsByKind(self, kind):
    output = []
    for module in self.raw.keys():
      for trans in self.raw[module].keys():
        if self.raw[module][trans].kind == kind:
          output.append(self.raw[module][trans])
    return output
    
  def calculateInheritedTransforms(self, toInherit):
    #Here, of all stupid places, is where we define inheritance (and the inheritance transform type happens.)
    #this is because the inheritance is like dynamic loaded stuff - the symbol for what it's
    #pointing at is deferred after loading everything from the source. well, this class is closest to after
    #the load as it gets;
#?after this each transform is ready to be used by the rest of the XC runtime proper
    
    #okay..
    #we prepend the rules from the original transform and use the same authority settings - so we don't
    #accidentally expose information when we make these inheritances.
    #the 'on error' of this transform takes precedence over the old ones (if present),
    #and the denied block of the inherit replaces the original, if any. There you go.
    gettingthemall = True
    iter = 0
    while gettingthemall:
      gotem = True
      for trans in toInherit:
        if trans.inheritFrom and not trans.inheritComplete:
          try:
            mod, tag, name = trans.inheritFrom.split('.')
          except:
            raise Exception, "At %s, please correct the transform name."%(trans.name)
          try:
            name = "%s.%s"%(self.raw[mod]["%s.%s"%(tag, name)].tag, name)
          except:
            raise "Error while inheriting transforms: The transform %s doesn't exist." % (str(trans.inheritFrom),)
          if self.raw[mod][name].inheritFrom:
            if not self.raw[mod][name].inheritComplete:
              pass #dbug("missed inheriting this round:" + trans.name)
              gotem = False
              continue 
#?map the requested type to inherit/preherit onto the inherited object:
          
          #flag to control where code is inserted
          pass #dbug("kind: "+trans.kind)
          if trans.kind.startswith('inherit'): 
            isInherit = True
          else:
            isInherit = False
              
          isAlias = False
          if trans.kind == 'inheritAlias':              
            isAlias = True
            trans.kind = self.raw[mod][name].kind
            
          elif trans.kind == 'inheritFilter':           trans.kind = 'filter'
          elif trans.kind == 'inheritFilterRestricted': trans.kind = 'filterRestricted'  
          elif trans.kind == 'inheritServer':           trans.kind = 'server' 
          elif trans.kind == 'inheritServerRestricted': trans.kind = 'serverRestricted'
          elif trans.kind == 'inheritDefine':           trans.kind = 'define' 
          elif trans.kind == 'inheritDefineRestricted': trans.kind = 'defineRestricted'
          elif trans.kind == 'inheritLaszlo':           trans.kind = 'laszlo' 
          elif trans.kind == 'inheritLaszloRestricted': trans.kind = 'laszloRestricted' 
            
          elif trans.kind == 'preheritFilter':          trans.kind = 'filter'
          elif trans.kind == 'preheritFilterRestricted':trans.kind = 'filterRestricted'  
          elif trans.kind == 'preheritServer':          trans.kind = 'server' 
          elif trans.kind == 'preheritServerRestricted':trans.kind = 'serverRestricted'
          elif trans.kind == 'preheritDefine':          trans.kind = 'define' 
          elif trans.kind == 'preheritDefineRestricted':trans.kind = 'defineRestricted'  
          elif trans.kind == 'preheritLaszlo':          trans.kind = 'laszlo' 
          elif trans.kind == 'preheritLaszloRestricted':trans.kind = 'laszloRestricted'    
#?Composite the new transform
          
          #   Generate authorization
          #//somtime: if every instance of new auth is in old, but less - make it less.
          pass #dbug("Pre/Inherit's authorization is: " + `trans.authorized` + " for trans: " + trans.name )
          if trans.authorized and self.raw[mod][name].authorized:
            newpermiss = Utils.intersect(trans.authorized, self.raw[mod][name].authorized)
            if newpermiss != []:
              pass #dbug("POST/INHERIT STAGE: POLICY: Group restricted, is now " + `newpermiss` +' which was: ' + `self.raw[mod][name].authorized`)
              trans.authorized = self.raw[mod][name].authorized
            else:
              msg = "POST/INHERIT STAGE: ERROR: the transform %s wants to redefine the security from %s to %s. It can only be set to something equal or more restrictive." %\
                      (trans.name, `self.raw[mod][name].authorized`, `newpermiss`)
              pass #dbug(msg)
              raise Exception, msg
          #if no transform specified, then keep the old authorization
          elif not trans.authorized:
            trans.authorized = self.raw[mod][name].authorized
          else:
            pass #dbug("INHERIT: POLICY: auth kept for " + trans.name )  
#? take the transform and add a fixed 'offset' to each command with a 'snapback' entry,
          #this realigns the if statements with where the rules are after the composition.
          inheritedRules = copy.deepcopy(self.raw[mod][name].rules[:-1])
          if not isAlias:
            if isInherit:
              for i, rule in enumerate(trans.rules):
                if Parser_Setup.rulesWithSnapback.count(rule[0]):
                  trans.rules[i][3] = trans.rules[i][3] + len(inheritedRules)
            else:
              for i, rule in enumerate(inheritedRules):
                if Parser_Setup.rulesWithSnapback.count(rule[0]):
                  inheritedRules[i][3] = inheritedRules[i][3] + len(trans.rules)
#?   put the rules in the right order; after or before inheriting is either append or prepend to the rules
          if isInherit: trans.rules = inheritedRules + trans.rules
          else:         trans.rules = trans.rules[:-1] + inheritedRules + [trans.rules[-1]]
#?little engine to take an original and new transform and correctly place their textblock subtransform
          #types to conform to the type of inheritance requested
          textHandlersToProcess = {self.raw[mod][name].documentHandler:[trans.documentHandler, '\n'],
                                   self.raw[mod][name].initspaceHandler:[trans.initspaceHandler, '\n'],
                                   self.raw[mod][name].defaultHandler:[trans.defaultHandler, ', ']}  
            
          for entry in textHandlersToProcess.keys():
            oldhandler = entry.rules[0][2]
            if not oldhandler:  continue
            newhandler = textHandlersToProcess[entry][0].rules[0][2]
            if newhandler:
              if isInherit: 
                textHandlersToProcess[entry][0].rules[0][2] = "%s%s%s"%(oldhandler, textHandlersToProcess[entry][1], newhandler)
              else:
                textHandlersToProcess[entry][0].rules[0][2] = "%s%s%s"%(newhandler, textHandlersToProcess[entry][1], oldhandler)      
            else:
              textHandlersToProcess[entry][0] = entry
          #END lil engine
            
          if not trans.deniedHandler.rules:
            trans.deniedHandler = self.raw[mod][name].deniedHandler
            
          if not trans.errorHandler:
            trans.errorHandler = self.raw[mod][name].errorHandler
            
          pass #dbug("finishing inheriting:"+trans.name)
          
          trans.inheritComplete = True
      if gotem:
        gettingthemall = False
        #iter MIGHT be recursion limit detection in the future
        iter = 0
      else:
        iter += 1
        
  def preCompile(self, trans, dictTarget, subprocess=True):
    #scan rules inside of one's self, looking for [~x~] rules that can be
    #pre compiled. If such is found, replace [~x~] with [~x~] where x is a hash into
    #the already compiled phrase. sounds easy nuff...
    try:
      if not trans.rules: 
        return #empty transform, nothing to do
    except:
      raise `trans.rules`
      
    for i, entry in enumerate(trans.rules): 
      #precompile python blocks
      if entry[0] == 'python':
        if type(entry[2]) is type(''):
          if self.evalsym.search(str(entry[2])):
            raise "At '%s' rule %s: Appear to have text replacement in a python block. Please correct it."%(trans.name, i)
          entry[2] = compile(entry[2]+'\n', trans.name, 'exec')
        continue
        
      #precompile attr dicts
      elif entry[0] == 'attr':
        if type(entry[2]) is type(''):
          if self.evalsym.search(str(entry[2])):
            raise "At '%s' rule %s: Appear to have text replacement in a python block. Please correct it."%(trans.name, i)
          entry[2] = compile("dict(%s)"%entry[2], trans.name, 'eval')
        continue
        
      #precompile context changes
      elif entry[0] == 'context':
        if type(entry[2]) is type(''):
          if self.evalsym.search(str(entry[2])):
            raise "At '%s' rule %s: Appear to have text replacement in a python block. Please correct it."%(trans.name, i)
          entry[2] = compile(entry[2], trans.name, 'eval')
        continue
        
      #precompile attr on 'new' blocks blocks
      elif entry[0].startswith('startwrapattr'):
        if type(entry[2]) is type(''):
          if self.evalsym.search(str(entry[2])):
            raise "At '%s' rule %s: Appear to have text replacement in a python block. Please correct it."%(trans.name, i)
          entry[2] = compile("dict(%s)"%entry[2], trans.name, 'eval')
        continue
        
      #precompile loop blocks
      elif entry[0].startswith('loop'):
        if type(entry[2]) is type(''):
          if self.evalsym.search(str(entry[2])):
            raise "At '%s' rule %s: Appear to have text replacement in a python block. Please correct it."%(trans.name, i)
          entry[2] = compile(entry[2], trans.name, 'eval')
        continue
        
      #precompile condition blocks
      elif entry[0] in ('if', 'elif'):
        if type(entry[2]) is type(''):
          if self.evalsym.search(str(entry[2])):
            raise "At '%s' rule %s: Appear to have text replacement in a python block. Please correct it."%(trans.name, i)
          entry[2] = compile(entry[2], trans.name, 'eval')
        continue
        
      #precompile attr on 'new' blocks blocks
      elif entry[0].startswith('startwrap'):
        for item in entry[1]:
          self.compileField(str(item), trans, dictTarget)
            
      self.compileField(entry[2], trans, dictTarget)
      
    try:
      if type(trans.defaultHandler.rules[0][2]) != type({}):
        trans.defaultHandler.rules[0][2] = eval("dict(%s)"%(trans.defaultHandler.rules[0][2]), dictTarget)
    except Exception, msg:
      raise Exception, "Name: %s using defaultHandler text %s has errors: %s"%(trans.name, trans.defaultHandler.rules[0][2], str(msg))
        
    if subprocess:
      self.preCompile(trans.deniedHandler, dictTarget, subprocess=False)
      for errortrans in trans.errorHandler:
        self.preCompile(errortrans, dictTarget, subprocess=False)
        
  def compileField(self, item, trans, dictTarget):
    """ search for [~x~] strings, compile them, and place that into the preCompile global dictionary
        for later. These are found all over the place, so are treated with this uniform scan!
    """
    #if not type(item) is type(''): return False
    origText = str(item)
    processList = []
    #okay - each time it finds a match record it's location (and extract interior to)
    #a processing list to consider in the next block. no match means it 'll skip the next loop.
    #i just got down with regexs again, so i think i'll be updating this soon.
    while 1:
      match = Instance.matchTextVar.search(origText)
      if not match: break
      x, y = match.span()
      fullvartext = origText[x:y]
      attrToReplace = origText[x+2:y-2]
      toreplace = [fullvartext, attrToReplace]
      if toreplace not in processList:
        processList.append(toreplace)
      origText = origText[y:]
  
    #else begin replacment of variables
    for entry in processList:
      fullvartext, attrToReplace = entry
      #okay, i've done this several (larger) ways, but let's just settle on a '?' operator for default goodness. all else should
      #be python eval strings. at one point there was a whole sub-language here, but that is prolly a confusing scene.
      if attrToReplace[0] == '?':
        buf = attrToReplace[1:].split('|')
        attrgiven = buf[0].strip()
        defaultArg = buf[1].strip()
        try:
          dictTarget[attrgiven] = compile(attrgiven+'\n', trans.name, 'eval')
        except Exception, msg:
          raise "Error compiling expression in:" + `trans.name` + str(msg) + ' content: ' + item
        try:
          dictTarget[defaultArg] = compile(defaultArg+'\n', trans.name, 'eval')
        except Exception, msg:
          raise "Error compiling expression in:" + `trans.name` + str(msg) + ' content: ' + item
        continue
      #escape text
      if attrToReplace[0] == '%':
        dictTarget[attrToReplace[1:]] = compile(attrToReplace[1:]+'\n', trans.name, 'eval')
        continue
      elif attrToReplace[0] in ['@', '*', '.', '$']:
        continue
      #Default: retrieve then eval() a value from the space associated with the transform.
      try:
        dictTarget[attrToReplace] = compile(attrToReplace+'\n', trans.name, 'eval')
      except Exception, msg:
        raise "Error compiling expression in:" + `trans.name` + str(msg) + ' content: ' + item
        
    return 

manager = Manager()

