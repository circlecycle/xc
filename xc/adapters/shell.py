
# Filename: adapters/shell.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)


#!EXPERIMENTAL! not ready for use

import sys
from xc import Instance, Manager
from xc.Utils import DefaultDict

class ShellRequestAdapter:
  """shell adapter is assumed to be running locally, like an adminstrator
     using the sys.argv for args, and other sensible defaults
  """
  
  def __init__(self, **kwargs):
    self._adapted = "shell"
    self._origreq = None
    self.app = None
    self.args = DefaultDict(dict([x.split('=') for x in sys.argv[1:]]))
    self.uri = [] 
    self.app = None
    self.ip = "127.0.0.1"
    self.login = "admin" #!make next two the active unix user
    self.user = "admin"
    self.sessid = "xxx" #!make this the active unix user + tty
    self.content_type = "text/html"
    self.response = ""

class Shell:
  def __init__(self):
    self.staticDefinition = "define fragment.INSTANCE"
    
  def read(self):
    while 1:
      block = []
      possibleClose = 0
      
      #? get a block to pass to the parser, terminated by two blank lines.
      while 1:
        buf = raw_input()
        if buf.strip() == "":  possibleClose += 1
        else:                  possibleClose = 0
        if possibleClose == 2: break
        block.append(buf)
        
      #?take the input and wrap it in a transform defintion *as if* it was a proper transform
      transform = ["  %s"%x for x in block]
      transform.insert(0, self.staticDefinition)
      print transform
      ##?this is passed to the parser to make the "CLI" module
      #
      #
      ##?Which is then called, passing the results back to the terminal if nothing went wrong
      #req = ShellRequestAdapter()
      #print Instance.Request(req).processXML(buf)