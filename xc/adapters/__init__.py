
# Filename: adapters/__init__.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#this seems to be a core dispatch pattern for integrating with web servers, so this
#is a good to way to centralize the (non-specific) server functionality.

import traceback, sys, re
from xc import Instance, Manager, Server, Config

sudoers = Config.setup.sudoers
process = Manager.manager.server.process
reload = Manager.manager.reload

def dispatch(req):
  """this is passed an ADAPTED request object. Returns that req object of which 
     then req.response does contain the XML string output."""
  global sudoers, process, reload
  path = req.uri.split('/')[2:]
  try: 
    #administrative functionality, specified by being in the sudoers group in the config.
    if path[0].startswith('_'):
      if req.sessionHandler.user in sudoers or req.ip == req._origreq.connection.local_ip:
        if path[0] == '_sessionCheck':
          req.response = str(Instance.Request(req).sessionCheck())
        elif path[0] == '_exit':
          Instance.Request(req).cleanExit()
          req.response = "_exit done, shouldn't see this.."
        elif path[0] == '_reload':  
          req.response = reload(req)
        elif path[0] == '_laszlo':  
          req.response = Instance.Request(req).loadLaszlo()
        elif path[0] == '_pack':  
          req.response = Instance.Request(req).packDB()
      else:
        req.response = '[access to admin urls denied]'  
    else:
      try:  
        #if it's html, find &nbsp and change it to unicode nonblank space.'
        if 'html' in req.content_type:
          req.response = process(req, path).replace('&amp;nbsp', '&#160')
        else:
          req.response = process(req, path)
      except Exception, msg:
        tback = `traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)`
        req.response = "Error in a server transform: %s: %s"%(msg, tback)
  except Exception, msg:
    req.response = `traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)`
  return req