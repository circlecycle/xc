#!/opt/local/bin/python

# Filename: adapters/plain.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#shows how to pass an xml document to the XC system
from xc import Instance, Manager

#default adapter
class RequestAdapter:
  def __init__(self, **kwargs):
    self._adapted = False
    self._origreq = None
    self.app = None
    self.args = ""
    self.uri = [] 
    self.app = None
    self.ip = ""
    self.login = "unauthorized"
    self.user = ""
    self.sessid = ""
    self.content_type = "text/html"
    self.response = ""

#one convenience function to generically 'kick off' the XC engine against
#a an xml string; a good baseline introduction the api..
def xcXML(buf):
  """Process some xml from your app through xc.."""
  req = RequestAdapter(user="admin", sessid="anystringwilldo")
  return Instance.Request(req).processXML(buf)
      
  
def reload():
  """simply advertising the reload the XC library function.."""
  Manager.reload()
  
def profile():
  import profile
  teststring = """<html __uses__="gnews"><body><div gnews.filterinterface="true"/></body></html>"""
  profile.run("""print processXML(teststring)""")

  

