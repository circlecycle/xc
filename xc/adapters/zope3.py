
# Filename: adapters/zope3.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

import sys
from xc.adapters import dispatch
from xc import Config, Instance

setup = Config.setup
  
#raise `dir(self.request)` + `dir(self.request.publication)` + ' : ' + `self.request._app_server` + `self.request.publication.getApplication(self.request)`

class ZopeRequestAdapter:
  """for interogation by the transforms during a request (mod_python request model as loose model for for it)"""
  def __init__(self, request, app=False):
    #global Instance
    self._adapted = "zope3"
    self._origreq = request
    self.content_type = "text/html"
    self.response = ""
    self.args   = request.get('QUERY_STRING')
    self.uri    = '/'+request.get('PATH_INFO')[1:]
    self.ip     = str(request.get('REMOTE_ADDR'))
    if not app: self.app = request.publication.getApplication(request)
    else:       self.app = app
    try:    self.sessid = str(IClientId(request))
    except: self.sessid = False
    id = getattr(request.principal, '_Principal__login', False)
    if not id:  id = request.principal.id.split('_')[-1]
    if id == 'zope.anybody':  id = 'anonymous'
    self.user = id
      
class ZopeInterface:
  def isSubPathHandled(self, path):
    path = path.split('/')
    if len(path) > 2:
      ##reload the XC library
      if path[0] == setup.serverPrefix: 
        return True
      elif path[1][0] == '_':
        return True
    return False
  
  def process(self, req, app):
    global dispatch
    return dispatch(ZopeRequestAdapter(req, app))
    
class XCLinked:
  """Inherit from this to get a nice way to call XC from zope views. Object this is applied to
     needs the attributes 'request' and 'context' under self, which is passed by zope by default.
     the fullpath attribute is the x.y form of the XC transform to call. Ideally, that transform is
     of the 'define' type, tho it doesn't have to be"""
     
  def callXC(self, fullpath):
    pathComponents = fullpath.split('.')
    module = pathComponents[0]
    if len(pathComponents) == 2:
      invokeTag = """<div %s.%s="true"/>""" % (pathComponents[0], pathComponents[1])
    elif len(pathComponents) == 3:
      invokeTag = """<%s %s.%s="true"/>""" % (pathComponents[1], pathComponents[0], pathComponents[2])
    else:
      raise Exception, "callXC() received an non-existant transform name, " + `pathComponents`
    ##THIS NEEDS TO GET APP SOMEHOW, SOON.
    req = ZopeRequestAdapter(self.request)
    result = Instance.Request(req, isServer=True).applyXC([module], invokeTag, context=self.context, request=self.request)
    return result
    
      
#bring zope stuff in (including publisher.py which depends on this module) 
#so it can be ready, but loads in the correct order (chicken/egg otherwise)
sys.path.append(setup.zopePath)

from zope.app.session.interfaces import IClientId
from zope.app.security.interfaces import IAuthentication
from zope.security.proxy import removeSecurityProxy
import zope.app.zapi