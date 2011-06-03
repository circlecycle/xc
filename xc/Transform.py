
# Filename: Transform.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#the transform module provides a class
#to hold 'rules'. Each instance of transform provides
#an in-order set of operations to (eventually)
#perform on a minidom tag object.
#so each Transform class represents
#the most basic aggregation of commands
#into what you could consider functions
#(or in DOM terms, event handlers --
#when x is encountered, apply transform y).

import sys, string, re, md5
import Parser_Setup
from Utils import dbug_func as dbug

#the means to recognize a text replacement section
matchTextVar = re.compile('((\[\~)[^\~]+?(\~\]))')

compiledExpressions = {}

class Names:
  names = {}
  counter = 0
  def getName(self, name):
    self.names[name] = "attr%s"%self.counter
    self.counter += 1
    return self.names[name]
  

class EmptyTextTransform:
  def __init__(self):
    #one empty rule.
    self.rules = [['','','']]

class EmptyTransform:
  def __init__(self):
    #one empty rule.
    self.rules = []

class Transform(object):
  names = Names()
  def __init__(self, kind, modulename, params):
    """throw in the init values to make a new transform of any type..
       this stores all naming info, authorization, inheritance, and 
       arrays that represent the list of 'rules' parsed from the the
       source code. A good place to start when becoming familiar with
       the other code, as these notions (obj and it's attributes) apply 
       themselves at every level of design. 
       
       The Context module, incidentally, is in concept the other half 
       of this. If you think of a transform as class in an OOP environment, 
       then the below would represent a definition (class), and the Context object would
       represent an instance of that class. Hrm, not so tough when seen that way. (ha.)"""
       
    self.modulename = modulename
    self.kind = kind
    self.shell = False
    self.rules = []
    self.authorized = False       #if there are NO restrictions on this transforms this is False
    self.inheritFrom = False
    self.inheritComplete = False
    
    #Handlers for various subtransforms, used to be dynamic via accessor, but futzed the picklin all but good..
    self.initspaceHandler = EmptyTextTransform()
    self.documentHandler = EmptyTextTransform()
    self.deniedHandler = EmptyTransform()
    self.errorHandler = []
    self.defaultHandler = EmptyTextTransform()
    self.laszloHandler = EmptyTransform()
    
    #per type initialization
    self.tag = params[0]
    self.trigger_attr = "%s.%s"%(params[0], params[1])
    self.name = "%s.%s"%(self.modulename, self.trigger_attr)
    self.atomicname = params[1]
    self.attrname = "%s.%s"%(self.modulename, params[1])
    self.scoredname = self.name.replace('.','_')
    self.shortname = self.names.getName(self.scoredname)
    #if this transform is a group protected type, interpret the third param 
    #as a comma separated list of groups. Too bad i don't know where else to cleanly put this..
    #I don't like tightly binding this class to a specific type of transform
    #and worse, with inherit it's the FOURTH argument, as the third is the inheritance target.
    if self.kind in Parser_Setup.restrictedTransforms:
      #inherited tranforms pass the inheritable item as the third, and auth as the fourth..
      if self.kind.startswith('inherit'):    self.authorized = params[3]
      elif self.kind.startswith('preherit'): self.authorized = params[3]
      else:                                  self.authorized = params[2]
      pass #dbug("AUTHRECEIVED:"+self.name+':'+`self.authorized` )
    if self.kind.startswith('inherit'):
      self.inheritFrom = params[2]
    elif self.kind.startswith('preherit'):
      self.inheritFrom = params[2]
    elif self.kind.startswith('shell'):
      self.shell = params[2]
    pass #dbug("NEW TRANSFORM: kind: '" + self.kind + "' name: '" + self.name +"' params: " + `params` )
    
  def __str__(self):
    return self.name
    
  def __repr__(self):
    return self.name

  def new(self, kind, params, value):
    self.rules.append([kind, params, value])
    
  def asciimd5(self, data): return str(md5.new(data).hexdigest())
    