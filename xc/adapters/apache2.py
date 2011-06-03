
# Filename: adapters/apache2.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#this uses mod_python, of course..

from mod_python import apache, Session, Cookie, util
from xc.adapters import dispatch
from xc import Utils
import time, os, random, md5, shelve, os.path
from xc import Config

def publisher(apacheReq):
  """The only "link" to mod_python/apache; this gets called on every request inbound."""
  #raise '\n'.join(["%s = %s"%(x, getattr(apacheReq, x)) for x in dir(apacheReq)])
  req = dispatch(ApacheRequestAdapter(apacheReq))
  apacheReq.content_type = req.content_type
  apacheReq.write(req.response)
  return apache.OK

class ApacheRequestAdapter:
  """These attributes are standardly used inside of xc. The values of the 
      attributes, given a mod_python request object, are what's being adapted."""
  def __init__(self, req):
    self._adapted = "mod_python"
    self._origreq = req
    self.app = None #(only Zope Adapter uses the app attribute)
    self.args = Utils.ArgsShell(util.FieldStorage(req))
    self.uri = req.uri
    self.ip = req.connection.remote_ip
    self.sessionHandler = SessionHandler(req) #call once per request only.
    self.content_type = "text/html"
    self.response = ""
  
class SessionHandler:
  users = {}
  unauthorized = 'anonymous'
        
  def __init__(self, req):
    """get, extract info, and do upkeep on the session cookie. This determines what the sessid and user are 
       for this request."""
    global UIDMaker
    #pass the request in making in so we can edit it later if requested (ACL for example)
    self.ip = req.connection.remote_ip
    c = Cookie.get_cookies(req)
    if not c.has_key('XCSession'):
      self.sessid = UIDMaker.new_sid(req)
    else:
      c = c['XCSession']
      self.sessid = c.value
      
    #make new cookie so the cycle continues
    c = Cookie.Cookie('XCSession', self.sessid)
    c.path = '/'
    Cookie.add_cookie(req, c)
    
    #save the path to this session.
    self.sessionPath = "%s/%s"%(Config.setup.sessionDir, self.sessid)
    
    #use previous authenication until cookie is reevaluated, if they are officially logged in (in Instance)
    if self.users.has_key(self.sessid):
      #if we have a record of their user in memory, use it
      self.user = self.users[self.sessid]
    else:  
      #if a SBD exists, use it as a source for current session's user
      realSessionPath = "%s%s"%(self.sessionPath, Config.setup.sessionExtension)
      if os.path.exists(realSessionPath):
        session = shelve.open(self.sessionPath, 'r')
        self.users[self.sessid]  = session['USER_']
        self.user = self.users[self.sessid]
        session.close()
      else:
        #They don't have on-disk session, so we don't know who they are.
        #if it's a normal request they'll go ahead with anonymous, and they
        #can login using the API to authorize. If it's not normal (login not called)
        #then there will be no session file of the request (think session checking and the like)
        self.user = self.unauthorized
    
  def login(self, user=False):
    #if a new user, save that with the shelf
    if user:  
      self.users[self.sessid] = user
      self.user = user
    else:
      #do they have memory credentials? if not then they are anonymous
      #record that.
      if not self.users.has_key(self.sessid):
        self.users[self.sessid] = self.unauthorized
    
    #make or update a session file for this request.
    #if the server is restarted, auth will be pulled from this file
    #based on the sessions' status.
    session = shelve.open(self.sessionPath, 'c')  
    session['USER_'] = self.users[self.sessid]
    session['TIMESTAMP_'] = int(time.time())
    session.close()
    
  def logout(self, sessid=False):
    """set the active session's entry in self.users to nothing, logging the user out."""
    if not sessid:  idtouse = self.sessid
    else:           idtouse = sessid
    
    #erase the session file and reset the in memory credentials
    realSessionPath = "%s/%s%s"%(Config.setup.sessionDir, idtouse, Config.setup.sessionExtension)
    os.remove(realSessionPath)
    #set them to anonymous for the rest of the request. The next
    #request will see a new round of initialization for them
    self.user = self.unauthorized
    self.users[idtouse] = self.unauthorized

#borrowed from the mod_python Session.py machinery
class Uid:
  def __init__(self):
    self.rnd_gens = self.init_rnd()
    self.rnd_iter = iter(self.rnd_gens)

  def init_rnd(self):
    """ initialize random number generators
    this is key in multithreaded env, see
    python docs for random """

    # query max number of threads
    gennum = apache.AP_MPMQ_MAX_SPARE_THREADS
    # make generators
    # this bit is from Python lib reference
    g = random.Random(time.time())
    result = [g]
    for i in range(gennum - 1):
      laststate = g.getstate()
      g = random.Random()
      g.setstate(laststate)
      g.jumpahead(1000000)
      result.append(g)
    return result

  def get_generator(self):
    # get rnd_iter.next(), or start over
    # if we reached the end of it
    try:
      return self.rnd_iter.next()
    except StopIteration:
      # the small potential for two threads doing this
      # seems does not warrant use of a lock
      self.rnd_iter = iter(self.rnd_gens)
      return self.rnd_iter.next()

  def new_sid(self, req):
    # Make a number based on current time, pid, remote ip
    # and two random ints, then hash with md5. This should
    # be fairly unique and very difficult to guess.

    t = long(time.time()*10000)
    pid = os.getpid()
    g = self.get_generator()
    rnd1 = g.randint(0, 999999999)
    rnd2 = g.randint(0, 999999999)
    ip = req.connection.remote_ip

    return md5.new("%d%d%d%d%s" % (t, pid, rnd1, rnd2, ip)).hexdigest()
    
    
UIDMaker = Uid()