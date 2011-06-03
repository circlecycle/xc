
# Filename: SessionSpace.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#there is  one class here. any reference to this module is using this class.

import sys, imp, copy, time, threading, urllib, weakref, os, shelve, traceback
from xml.dom.minidom import parse, parseString
import Manager, Config

setup = Config.setup

#define those types we SHOULDN'T pickle for use later.
def testfunc(): pass
class testclass: pass
domelem = parseString("""<div>hi</div>""").documentElement  
badtypes = [type(testfunc), type(testclass), type(imp.new_module('dummy')), type(domelem)]
        
#this class is a singleton used in Instance.py to get and manage active namespaces in and out of
#memory and the DB.
class New:
  def __init__(self):
    global badtypes
    """new returns a new namespace, or an old one if already requested."""
    self.spaces = {}
    self.lastAccess = {}
    self.lastspacecheck = False
    self.lastspacedbcheck = False
    self.lib = Manager.manager.library.raw
    self.spaceTimeoutCheck = int(Config.setup.spaceTimeoutCheck)
    self.sessionTimeoutCheck = int(Config.setup.sessionTimeoutCheck)
    self.badtypes = badtypes

    self.debug = ['Sessions Checked']
    
    #start a thread that does nothing but periodically hit a special url to trigger
    #session cleanup. Since the routine won't respond to any requests except from localhost,
    #this isn't a big deal to do it this way. This offers the threading, resources, etc. of a 
    #"real" request which is precisely what i need.
    self.sessioncleaner = threading.Thread(target=self.sessionCheckerThread)
    self.sessioncleaner.setDaemon(True)
    self.sessioncleaner.start()
    
  def sessionCheckerThread(self):
    """so all we do here is call sessioncheck over and over using a urllib request.
      this is it's own perpetual thread as long as the #self.debug system is up. look at
      __init__ for the threading call. This is a bit convoluted, in the the ACTUAL call
      to sessionChecker (which does the work) comes from the Request() class, because
      the resources of a request are exactly what we need, aka a new thread and a new 
      connection to storage. the _sessionCheck prefix on the url does this, and is 
      hardcoded into the adapters to call when needed. won't work if not on localhost 
      (as enforced in the Request() function sessionCheck()'"""
    sessionCheckInterval = int(Config.setup.sessionCheckInterval)
    url = "%s%s/_sessionCheck"%(Config.setup.baseUrl, Config.setup.serverPrefix)
    while 1:
      time.sleep(sessionCheckInterval)
      try:  
        results = urllib.urlopen(url).read()
      except Exception, msg:
        #self.debug.append("Failed making a request to session check.", str(msg))
        pass
        
  def sessionChecker(self, req):
    #force a session check using a query string var
    if req.args['force']:
      self.dumpOldSpacesToDB()
      self.removeOldSpacesFromDB(req.acl)
      return "Forced session check"
       
    #ghead and see if the time for a check has come
    currtime = int(time.time())
    #self.debug.append('checking at %s'%currtime)
       
    if not self.lastspacecheck:
      self.lastspacecheck = currtime
    if not self.lastspacedbcheck:
      self.lastspacedbcheck = currtime
      
    #self.debug.append('lastspacecheck at %s'%self.lastspacecheck)
    #self.debug.append('lastspaceDBcheck at %s'%self.lastspacedbcheck)
      
    #self.debug.append('lastspacecheck scheduled for (when <) %s'%(self.lastspacecheck + self.spaceTimeoutCheck))
    if self.lastspacecheck + self.spaceTimeoutCheck < currtime:
      #self.debug.append('Trying to dump old spaces TO db at %s'%currtime)
      self.dumpOldSpacesToDB()
      self.lastspacecheck = currtime

    #self.debug.append('lastspaceDBcheck scheduled for (when <) %s'%(self.lastspacedbcheck + self.sessionTimeoutCheck))
    if self.lastspacedbcheck + self.sessionTimeoutCheck < currtime:
      #self.debug.append('Trying to erase old sessions FROM db at %s'%currtime)
      self.removeOldSpacesFromDB(req.acl)
      self.lastspacedbcheck = currtime
      
    #a blank line in each debug block
    #self.debug.append('')
    
  def getSpaceFor(self, acl, module):
    """return the appropiate space, or returns a new one
       if it hasn't been assigned to yet.
    """
    #do the logic to make the session if none, the module if none.
    #this also reloads the session from the zodb machinery, if any!
    if self.spaces.has_key(acl.sessid):
      if not self.spaces[acl.sessid].has_key(module):
        self.spaces[acl.sessid][module] = imp.new_module('space')
        space = self.spaces[acl.sessid][module]
        #This is needed to decide what init block have been run, may be filled on session reload
        space.INITSPACETRACKER = {}
        #This records which automatically generated ID numbers the session had been using
        space.AUTOGENTABLE = {}
      else:
        space = self.spaces[acl.sessid][module]
    else:
      #if session doesn't exist, make the session, then module.
      self.spaces[acl.sessid] = {module:imp.new_module('space')}
      space = self.spaces[acl.sessid][module]
      #This is needed to decide what init block have been run, may be filled on session reload
      space.INITSPACETRACKER = {}
      #This records which automatically generated ID numbers the session had been using
      space.AUTOGENTABLE = {}
      
    return space
    
  def updateLastAccess(self, sessid):
    #Keep an inmemory structure so we don't have to open files to check for staleness.
    self.lastAccess[sessid] = int(time.time())
    
  def saveAllSpacesToDB(self):
    global setup
    #save all outstanding spaces to the DB - shutdown, prolly.
    #self.debug.append('saving all session db: %s'%self.spaces)
    for sessid in self.spaces.keys():
      #self.debug.append('saving %s: %s'%(sessid, self.lastAccess[sessid]))
      sessionPath = "%s/%s"%(setup.sessionDir, sessid)
      session = shelve.open(sessionPath, 'c')
      self.saveSpacesToDB(session, self.spaces[sessid])
      del self.lastAccess[sessid]
      del self.spaces[sessid]
      session.close()
    
  def saveSpacesToDB(self, session, space):
    """get all attributes from all modules in sessid and return a dictionary
       containing only those attributes that aren't prefixed by underscores,
       aren't UPPERCASE (builtins) and aren't badtypes (functions, modules, etc)
    """
    try:
      #erase everything but metadata (which ends with '_')
      #self.debug.append('saving the session space %s'%(space))
      moddata = {}  
      for mod in space.keys():
        if self.lib[mod].has_key('._STATELESS'):
          continue
        
        if self.lib[mod].has_key('._STATEFUL'):
          #save the kit and the kaboodle: save the entire namespace to a dictionary, MINUS
          #builins (uppercase), dom nodes, things with leading underscores, function and class definitions..
          #what else am i missing? see badtypes at the top of the module to add more. 
          subspaces = space[mod].SELFS
          strippedspaces = {}
          for key in [x for x in subspaces.keys() if not x.startswith('_')]:
            strippedspaces[key] = {}
            for attr in [x for x in subspaces[key].keys() if not x.startswith('_')]:
              strippedspaces[key][attr] = subspaces[key][attr]
            if not strippedspaces[key]:
              del strippedspaces[key]
          
          moddata[mod] = {'INITSPACETRACKER' :space[mod].INITSPACETRACKER, 
                         'AUTOGENTABLE'     :space[mod].AUTOGENTABLE, 
                         'SELFS'            :strippedspaces}
          
          #iterate and save all the appropiate attributes from the space to be saved into the zo-diggity-B.
          badtypes = self.badtypes
          for entry in space[mod].__dict__.keys():
            if entry and not entry.startswith('_'):
              if entry.upper() != entry:
                if entry != 'self':
                  attr = space[mod].__dict__[entry]
                  if type(attr) not in badtypes:
                    moddata[mod][entry] = attr
        else:
          #if it's not stateful then just save the autoGenTable (important for ajax continuations? think so)
          moddata[mod] = {'AUTOGENTABLE':space[mod].AUTOGENTABLE}
        
        #set the modules' state in the zodb (via frozenspaces)
        #we'll want to retrieve it one by one on module load later.
        try:
          session[mod] = moddata[mod]
        except:
          raise 'cant store in the session: mod %s, content%s'%(mod, `moddata[mod]`)
    except Exception, msg:
      print "bomb saving session:", str(msg)
      
  def loadSpaceFromDB(self, acl, mod):
    #now load all the saved attributes from the session
    session = shelve.open(acl.sessionHandler.sessionPath, 'c')
    if session.has_key(mod):
      #set the scene
      translib = self.lib[mod]
      targetspace = self.spaces[acl.sessid][mod].__dict__
      moddata = session[mod]
      #if it is not a 'stateful' module, no need to load it.
      if self.lib[mod].has_key('._STATEFUL'): 
        #run all the init blocks THAT HAVE ONLY BEEN RUN PREVIOUSLY (yay!) Order shouldn't matter..
        #this uses the list in INITSPACETRACKER and runs those initblocks in the new space.
        if moddata.has_key('INITSPACETRACKER'):
          for toinit in moddata['INITSPACETRACKER'].keys():
            if translib.has_key(toinit):
              targetinit = translib[toinit].initspaceHandler
              exec targetinit.rules[0][2] in targetspace

      #repopulate the space with the saved values and we be on our way!
      for entry in moddata.keys():
        targetspace[entry] = moddata[entry]

      #delete the module we just reloaded from the sesson
      del session[mod]
    session.close()
  
  def dumpOldSpacesToDB(self):
    #scan all sessions, looking for spaces to shift to the zodb.
    timeout = int(Config.setup.spaceTimeout)
    currtime = int(time.time())
    for sessid in self.lastAccess.keys():
      #self.debug.append('inspecting the session space %s: %s'%(sessid, self.lastAccess[sessid]))
      lastaccess = int(self.lastAccess[sessid])
      if lastaccess + timeout < currtime:
        #self.debug.append('removing the session space %s'%(sessid))
        sessionPath = "%s/%s"%(setup.sessionDir, sessid)
        session = shelve.open(sessionPath, 'c')
        self.saveSpacesToDB(session, self.spaces[sessid])
        del self.lastAccess[sessid]
        del self.spaces[sessid]
        session.close()
    
  def removeOldSpacesFromDB(self, acl):
    #presumably we call this whenever we feel like it.
    timeout = int(Config.setup.sessionTimeout)
    currtime = int(time.time())
    sesslist = [x.split('.')[0] for x in os.listdir(setup.sessionDir) if not x.startswith('.')]
    for sessid in sesslist:
      #check lastAccess (with loaded memory session info) because if they are in there and this is timed out,
      #it just means they've been active the whole time. when they are dumped, the timestamp will be updated and
      #their normal timeout period will begin. (edge case..)
      try:
        #self.debug.append('inspecting the session db %s'%(sessid))
        if not self.lastAccess.has_key(sessid):
          #remember to respect possible extensions on db file (Grrrrrrr!)
          sessionPath = "%s/%s%s"%(setup.sessionDir, sessid, setup.sessionExtension)
          session = shelve.open(sessionPath, 'r')
          #self.debug.append('determing staleness of %s at %s'%(sessid, session.keys()))
          
          #get timestamp. If the file doesn't have one (how!?) then just log them out.
          try: 
            timestamp = int(session['TIMESTAMP_'])
          except:
            session.close()
            acl.logout(sessid=sessid)
            
          if timestamp + timeout < currtime:
            #self.debug.append('STALE - erasing session and logging out %s'%(sessid))
            #logout the session (if logged in still.)
            session.close()
            acl.logout(sessid=sessid)
          else:
            session.close()
            
      except Exception, msg:
        raise ''.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))        
      
      

 