
# Filename: Server.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

import sys, string, os, xml.sax.saxutils
from xml.dom.minidom import parse, parseString
import Instance, Config

setup = Config.setup

esc = xml.sax.saxutils.escape

class ServerRoot:
  """This object is assembled from the generated classes representing modules.
     by organizing hierarchly, mod_python will be able to traverse and display
     these functions as urls!"""
     
  metatypes = {
    'jpg':  "image/jpeg",
    'gif':  "image/gif",
    'png':  "image/png",
    'js':   "text/javascript",
    'html': "text/html",
    'htm':  "text/html",
    'xul':  "text/xul",
    'css':  "text/css",
    'pdf':  "text/pdf",
    'swf':  "application/x-shockwave-flash",
    'mp3':  "audio/mpeg",
  }
  
  hiddenPathPrefixes = ['.','_']
     
  def __init__(self, library):
    self.library = library
    self.loadServerTransforms()
    
  def loadServerTransforms(self):
    self.tsd = {}
    for trans in self.library.getAllTransformsByKind('server'):  
      self.tsd['%s.%s'%(trans.modulename,trans.atomicname)] = trans
    for trans in self.library.getAllTransformsByKind('serverRestricted'):  
      self.tsd['%s.%s'%(trans.modulename,trans.atomicname)] = trans
    for trans in self.library.getAllTransformsByKind('serverPage'):  
      self.tsd['%s.%s'%(trans.modulename,trans.atomicname)] = trans
    
    
  def run(self, req, trans, instance='all', extrapath=[]):
    """Given arguments passed from mod_python and the transform invoked,
       run a transform within its given namespace and argument requirements."""
    #if it's a server 'page' then process it as a top-level document, bells and whistles.
    if trans.kind == 'serverPage':
      tagString = """<html __uses__="%s"><body><%s %s="true"/></body></html>"""%(trans.toImport, trans.tag, trans.attrname)
      return Instance.Request(req, extrapath=extrapath).processXML(tagString)
    #if it's a 'normal' server call, then do it so that it's a straight process - no executing of start, finish blocks that
    #would ordinarily prepare the page.. a server call usually means a page has already been sent to the client (think ajax)
    else:
      tagString = """<%s %s="true"/>"""%(trans.tag, trans.attrname)
      return Instance.Request(req, isServer=True, extrapath=extrapath).processFragment(tagString, [trans.modulename], scansingle=trans.trigger_attr, saveas=instance, topmost=True)
    
  def process(self, req, normalizedPath):
    path = normalizedPath
    #See if the uri points at a transform. if it does invoke it using the run() function
    instance = path[1].split('?')[0].split('+')
    if len(instance)>1:  
      topname = instance[0]
      instance = instance[1]
    else:                
      topname = instance[0]
      instance = 'all'
    #do we have a server by this name, factoring out "+" and "?" sections, eg module.transform+one?hello=world&
    transname = "%s.%s" % (path[0], topname)
    if self.tsd.has_key(transname):
      return self.run(req, self.tsd[transname], instance=instance, extrapath=path[2:])
        
    #Hide dot files and dirs and don't serve transform modules ending in .xc
    try:
      if sum([True for x in path if x[0] in self.hiddenPathPrefixes]) or path[1].endswith('.xc'):
        self.gracefulBowout(str('/'.join(path)))
    except:
      self.gracefulBowout(`path`)
      
    #check to see if it's a file in the dir!! auto publishing, go!
    realdir = '/'.join(path[:-1])
    realpath = '%s/%s'%(realdir,path[-1])

    #singeltonize the listing of files to only happen one time, aka {}?
    try:
      filelist = os.listdir('%s%s'%(setup.basePath,realdir))
    except:
      raise str("The requested directory, "+realdir+", does not exist.")
    if path[-1] in filelist:
      fileContents = file(setup.basePath+realpath).read()
      #guess meta type
      extension = path[-1].split('.')[-1]
      if self.metatypes.has_key(extension):
        req.content_type = self.metatypes[extension]
      # if it's html, send it through the XC processor. cool!
      if req.content_type == 'text/html': 
        return Instance.Request(req).processXML(fileContents)
      else: 
        return fileContents
    #except Exception, msg:
    #  raise Exception, "there is nothing at this url. <br/><br/>%s" % esc(str(msg))
    self.gracefulBowout(realpath)
    
    
  def gracefulBowout(self, realpath):
    raise str("There is nothing at this url: %s" % (str(realpath)))
