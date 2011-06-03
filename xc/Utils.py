
# Filename: Utils.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

import sys, imp, urllib, re, copy, string, random, time, os
from xml.dom.minidom import parse, parseString

#Some utilities that don't warrant a module of their own, really
  
class Logger:
  data = []
  def log(self, msg):
    self.data.append(msg)  
  def report(self):
    return `self.data`
    return '\n'.join(self.data)
  
class DefaultDict:
  """This dictionary will return None if key not present instead of excepting, which cuts a lot of deadwood code."""
  def __init__(self, dictIn={}):
      self.__dict__ = dictIn 
      
  def keys(self):
    return self.__dict__.keys()
    
  def has_key(self, key):
    return self.__dict__.has_key(key)

  def __getitem__(self, key):
    try:
      return self.__dict__[key]
    except KeyError: 
      return None
      
class DictToObjWrapper:
  """This is a dictionary that allows setting and getting through attributes instead of
     the [] syntax. That's all.'"""
  def __init__(self, target):
    self.__dict__['__orig'] = target
    
  def has_key(self, key):     
    return self.__dict__['__orig'].has_key(key)
    
  def keys(self):        
    return self.__dict__['__orig'].keys()
    
  def __getitem__(self, attr):
    return self.__dict__['__orig'][attr]
    
  def __setitem__(self, attr, value):
    self.__dict__['__orig'][attr] = value
    
  def __getattr__(self, attr):
    return self.__dict__['__orig'][attr]
    
  def __setattr__(self, attr, value):
    self.__dict__['__orig'][attr] = value
    
class DictToSpaceWrapper:
  """This is a dictionary that allows setting and getting through attributes in addition to
     the [] syntax. That's all.'"""
  def __init__(self, target={}):
    self.__dict__ = target
    self.__dict__['self'] = self
    
  def __str__(self):
    return str(self.__dict__)
    
  def __repr__(self):
    return `self.__dict__`
    
  def has_key(self, key):     
    return self.__dict__.has_key(key)
    
  def keys(self):        
    return self.__dict__.keys()
    
  def __getitem__(self, attr):
    return self.__dict__[attr]
    
  def __setitem__(self, attr, value):
    self.__dict__[attr] = value
    
  def __getattr__(self, attr):
    return self.__dict__[attr]
    
  def __setattr__(self, attr, value):
    self.__dict__[attr] = value
      
class DefaultList(list):
  """This list will return None if key not present instead of excepting, which cuts a lot of deadwood code."""
  def __getitem__(self, num):
    if num < len(self): return self[num]
    else:               return False
      
class DefaultPathList(list):
  """This list will return None if key not present instead of excepting, which cuts a lot of deadwood code."""

  def __str__(self):
    return '/'.join(self)
  
class DefaultTypeDict:
  """This dictionary will set&return key to [] (by default) if key not present."""
  def __init__(self, defaultType=[]):
    self.__defaultType = defaultType
  
  def keys(self):
    return self.__dict__.keys() 
    
  def has_key(self, key):
    return self.__dict__.has_key(key)
    
  def __str__(self):
    return str(self.__dict__)
  
  def __repr__(self):
    return `self.__dict__`
    
  def __setitem__(self, name, value):
    self.__dict__[name] = value
    
  def __getitem__(self, name):
    if self.__dict__.has_key(name):
      return self.__dict__[name]
    else:
      self.__dict__[name] = self.__defaultType
      return self.__dict__[name]
      
class DefaultSpacesDict:
  """This dictionary will set&return key to [] (by default) if key not present."""
  def __init__(self, dictIn={}):
    self.__dict__ = dictIn
  
  def keys(self):
    return self.__dict__.keys() 
    
  def has_key(self, key):
    return self.__dict__.has_key(key)
    
  def __str__(self):
    return str(self.__dict__)
  
  def __repr__(self):
    return `self.__dict__`
    
  def __setitem__(self, name, value):
    self.__dict__[name] = value
    
  def __getitem__(self, name):
    global DictToSpaceWrapper
    if self.__dict__.has_key(name):
      return self.__dict__[name]
    else:
      self.__dict__[name] = DictToSpaceWrapper()
      return self.__dict__[name]

class AttrShell:
  """This will wrap a minidom attributes object, which cuts a lot of deadwood code."""
  def __init__(self, tag):
    self.tag = tag
  
  def keys(self):
    return self.tag.attributes.keys()
    
  def has_key(self, k):
    return self.tag.attributes.has_key(k)
    
  def __str__(self):
    return str(self.tag.attributes).encode('utf-8')
  
  def __repr__(self):
    return `self.tag.attributes.encode('utf-8')`
    
  def __getitem__(self, name):
    return self.tag.getAttribute(name).encode('utf-8')
    
  def __setitem__(self, name, value):
    return self.tag.setAttribute(name, value)
    
class ArgsShell:
  def __init__(self, fs):
    self.fs = fs
    
  def __getitem__(self, key):
    return self.fs.get(key, None)
    
  def keys(self):
    return self.fs.keys()
    
  def has_key(self, key):
    return self.fs.has_key(key)
    
  def upload(self):
    if self.fs.has_key('Filename'): return (self.fs['Filename'].value, self.fs['Filedata'].value)
    else:                           return None

class ArgvShell(str):
  """ 
      This can wrap lists or dicts.
      
      This will wrap an array object, which cuts a lot of deadwood code.
      this chooses to send a string to be evaled or just the normal comma delim text mode, by
      prefixing $$ to the string passed - this will be eval'ed instead, finally allowing 
      real python objects to be passed between subcalls. neat. Alot of the time you don't need this 
      and eval() is expensive, so it's only invoked if needed.
  """
  stacksym = re.compile('\%\%')
  
  def __init__(self, rawstring):
    self.rawstring = rawstring
    
  def __str__(self):
    return self.rawstring
    
  def __repr__(self):
    return `self.array`
  
  def using(self, passstack={}):
    if passstack and self.stacksym.search(self.rawstring):
      key = str(self.rawstring[2:].strip())
      self.argv = passstack[key]
      self.array = passstack[key]
      #del passstack[key]
    elif not self.rawstring == 'true':
      self.array = [x.encode('utf-8').strip() for x in self.rawstring.split(',')]
      self.argv = dict([(i, x) for i, x in enumerate(self.array)])
    else:
      self.argv = {}
      self.array = []
    return self
      
  def __getitem__(self, index):
    try:    return self.argv[index]
    except: return None
      
  def __getslice__(self, start, stop):
    return self.array[start:stop]
      
  def __setitem__(self, index, value):
    self.argv[index] = value
      
  def keys(self):
    return self.argv.keys()
    
  def has_key(self):
    return self.argv.has_key()
      
  def __call__(self):
    return self.argv
  
class ArgvMacroShell(str):
  """ 
      This can wrap lists or dicts.
      
      This will wrap an array object, which cuts a lot of deadwood code.
      this chooses to send a string to be evaled or just the normal comma delim text mode, by
      prefixing $$ to the string passed - this will be eval'ed instead, finally allowing 
      real python objects to be passed between subcalls. neat. Alot of the time you don't need this 
      and eval() is expensive, so it's only invoked if needed.
  """
  stacksym = re.compile('\%\%')
  
  def __init__(self, rawstring):
    self.rawstring = rawstring
    
  def __str__(self):
    return self.rawstring
    
  def __repr__(self):
    return `self.array`
  
  def using(self, passstack={}):
    if passstack and self.stacksym.search(self.rawstring):
      key = str(self.rawstring[2:].strip())
      self.argv = passstack[key]
      self.array = passstack[key]
    else:
      if self.rawstring != 'true':
        self.array = [x.encode('utf-8').strip() for x in self.rawstring.split(',')]
        self.argv = dict([(i, x) for i, x in enumerate(self.array)])
      else:
        self.array, self.argv = [], {}
        
    return self
      
  def __getitem__(self, index):
    return self.argv[index]
      
  def __getslice__(self, start, stop):
    try: return self.array[start:stop]
    except: return []
      
  def __setitem__(self, index, value):
    self.argv[index] = value
      
  def keys(self):
    return self.argv.keys()
    
  def has_key(self):
    return self.argv.has_key()
      
  def __call__(self):
    return self.argv
    
class AutoShell(str):
  """ 
     this is a SINGLETON.
     
     add the new uid to the Auto List that tracks the recursive structure of automatically generated names.
     it has a set of behaviors that make it either a string or a list, where the string is the current name
     and the list is fifo stack. 
  """  
  def prepare(self, stack):
    self.stack = stack
    return self
    
  def keys(self):
    return [str(x['AUTO']) for x in self.stack.autolist]
    
  def __getitem__(self, index):
    return str(self.stack.get('AUTO', index))
  
class StackShell:
  """ 
     this is a SINGLETON.
     
     add the new uid to the Auto List that tracks the recursive structure of automatically generated names.
     it has a set of behaviors that make it either a string or a list, where the string is the current name
     and the list is fifo stack. 
  """
  stacksym = re.compile('\%\%')

  def __init__(self):
    self.autolist = []
    self.buf = []
  
  def add(self, state):
    self.autolist.append(state)
    
  def remove(self):
    self.buf.append(self.autolist.pop()['AUTO'])
    
  def keys(self):
    return self.autolist[-1].keys()
      
  def get(self, name, index=-1):       
    return self.autolist[int(index)][name]

class IndexShell(int):
  """This will wrap an array object, which cuts a lot of deadwood code."""
  def setlist(self, rawlist):
    self.rawlist = rawlist
    return self
    
  def __getitem__(self, index):        
    return self.rawlist[index]
      
class Indexer(int):
  """takes a number and return-and-increments it on 'tick'"""
  def tick(self):
    self += 1
    return self-1
    
  def untick(self):
    self -= 1
    return self
  
def GetIndent(buf):
  return len(buf) - len(string.lstrip(buf))

def JumpToNextMacro(toload, i):
  extent = int(i)
  gotit = False
  while extent < len(toload):
    if not GetIndent(toload[extent]) and toload[extent][0] != '#':
      gotit = True
      break
    extent += 1
  if not gotit: return False
  else:         return extent + 1
    
def RecurString(buf, typeis='str', topmost=True):
  if getattr(buf, 'array', False):  
    return buf.rawstring
  elif getattr(buf, 'append', False):
    for i, entry in enumerate(buf):
      buf[i] = RecurString(entry, typeis=typeis, topmost=False)
  elif getattr(buf, 'fromkeys', False):
    for key in buf.keys():
       buf[key] = RecurString(buf[key], typeis=typeis, topmost=False)
  if not topmost and not (getattr(buf, 'append', False) or getattr(buf, 'fromkeys', False)):
      return str(buf)
  return buf
  
  
def countAndRemoveBeginningChars(attrToReplace, char):
  """given a string and character, count how many are at the start and return the 
     newstring and the number found. useful in parsing certain textreplacement syntaxes."""
  numToRemove = 0
  while numToRemove < len(attrToReplace) and attrToReplace[numToRemove] == '?': 
    numToRemove += 1
  #numToRemove has the number of question marks that were present
  return (attrToReplace[numToRemove:], numToRemove)
    
    
class PlistParser:
  """take the topmost strings from a plist and return a object with
     them as attributes inside of it."""
  def __init__(self, plistPath, destinationSpace=None):
    #load plist
    configdata = {}
    plist = parseString(open(plistPath).read())
    
    #strip extraneous text nodes and get the root node 'dict'
    nodesToLoad = \
      [x for x in 
        plist.getElementsByTagName('dict')[0].childNodes 
          if x.nodeType == x.ELEMENT_NODE]
        
    #extract key/value string pairs, with a toggle state machine    
    for node in nodesToLoad:
      if node.tagName == 'key':   
        lastkey = str(node.firstChild.nodeValue)
        
      elif node.tagName == 'string':  
        if node.firstChild:
          configdata[lastkey] = str(node.firstChild.nodeValue).strip()
        else:
          configdata[lastkey] = ''
        lastkey = None
    
    #if no space targeted just return a new object with strings loaded as attributes
    #in it. probably the more common usage.
    if destinationSpace == None:
      destinationSpace = self
    
    #assign the extracted string variables to the namespace targetted, and we're done. 
    for varToSet in configdata.keys():
      setattr(destinationSpace, varToSet, configdata[varToSet]) 
      
class CacheHandler:
  """Namespaces agin' i tell ya! This holds a dict object represeting a previous
     calulation in a python block, and exposes methods to check the validity and update the 
     namespace cached. Yeah, cached namespaces :)
     Unique keys are the responsibility of the user..
  """

  def __init__(self):
    self.store = {}

  def update(self, keydex, timelimit, data):
    self.store[keydex] = [self.stamp(), timelimit, data]

  def valid(self, keydex):
    if self.store.has_key(keydex):
      if (self.stamp() - self.store[keydex][0]) < self.store[keydex][1]: 
        return True
    return False

  def get(self, keydex):
    return self.store[keydex][2]

  def stamp(self):
    return int(time.time())

  def clean(self):
    now = self.stamp()
    for cachekey in self.store.keys():
      if (now - self.store[cachekey][0]) > self.store[keydex][1]:
        del self.store[cachekey]

  def reset(self):
    self.store = {}
  

def intersect(set1, set2):
  """
  Returns intersection of tuples/lists of data

  """
  results = []
  for entry in set1:
    if entry in set2:
      results.append(entry)
  return results
  
def splitinto(amt, obj):
  """take a flat list and break it into parts where each
     subarray is amt long, or less. For formatting blocks, mostly"""
  output, buf = [], []
  for i, entry in enumerate(obj):
    buf.append(entry)
    if i%amt == amt-1:
      output.append(buf)
      buf = []
  
  if buf: output.append(buf)
  return output
  
  
dbugs = []  
def dbug_func(msg):
  global dbugs
  """simple debug printing"""
  dbugs.append(msg+'\n')

#now just a util function...

#########################################################
# md5crypt.py
#
# 0423.2000 by michal wallace http://www.sabren.com/
# based on perl's Crypt::PasswdMD5 by Luis Munoz (lem@cantv.net)
# based on /usr/src/libcrypt/crypt.c from FreeBSD 2.2.5-RELEASE
#
# MANY THANKS TO
#
#  Carey Evans - http://home.clear.net.nz/pages/c.evans/
#  Dennis Marti - http://users.starpower.net/marti1/
#
#  For the patches that got this thing working!
#
#########################################################
"""md5crypt.py - Provides interoperable MD5-based crypt() function

SYNOPSIS

  import md5crypt.py

  cryptedpassword = md5crypt.md5crypt(password, salt);

DESCRIPTION

unix_md5_crypt() provides a crypt()-compatible interface to the
rather new MD5-based crypt() function found in modern operating systems.
It's based on the implementation found on FreeBSD 2.2.[56]-RELEASE and
contains the following license in it:

 "THE BEER-WARE LICENSE" (Revision 42):
 <phk@login.dknet.dk> wrote this file.  As long as you retain this notice you
 can do whatever you want with this stuff. If we meet some day, and you think
 this stuff is worth it, you can buy me a beer in return. Poul-Henning Kamp

apache_md5_crypt() provides a function compatible with Apache's
.htpasswd files. This was contributed by Bryan Hart <bryan@eai.com>.

"""

MAGIC = '$1$'   # Magic string
ITOA64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

import md5

def to64 (v, n):
  ret = ''
  while (n - 1 >= 0):
    n = n - 1
  ret = ret + ITOA64[v & 0x3f]
  v = v >> 6
  return ret

def apache_md5_crypt (pw, salt):
  # change the Magic string to match the one used by Apache
  return unix_md5_crypt(pw, salt, '$apr1$')


def unix_md5_crypt(pw, salt, magic=None):
  if magic==None:
    magic = MAGIC
  # Take care of the magic string if present
  if salt[:len(magic)] == magic:
    salt = salt[len(magic):] 

  # salt can have up to 8 characters:
  import string
  salt = string.split(salt, '$', 1)[0]
  salt = salt[:8]

  ctx = pw + magic + salt

  final = md5.md5(pw + salt + pw).digest()

  for pl in range(len(pw),0,-16):
    if pl > 16: ctx = ctx + final[:16]
    else:   ctx = ctx + final[:pl]


  # Now the 'weird' xform (??)

  i = len(pw)
  while i:
    if i & 1: ctx = ctx + chr(0)
    else:   ctx = ctx + pw[0]
    i = i >> 1

  final = md5.md5(ctx).digest()
  
  # The following is supposed to make
  # things run slower. 

  # my question: WTF???

  for i in range(1000):
    ctx1 = ''
    if i & 1: ctx1 = ctx1 + pw
    else:   ctx1 = ctx1 + final[:16]
      
    if i % 3: ctx1 = ctx1 + salt
    if i % 7: ctx1 = ctx1 + pw

    if i & 1: ctx1 = ctx1 + final[:16]
    else:   ctx1 = ctx1 + pw
      
    final = md5.md5(ctx1).digest()


  # Final xform             
  passwd = ''
  passwd = passwd + to64((int(ord(final[0])) << 16)
               |(int(ord(final[6])) << 8)
               |(int(ord(final[12]))),4)
               
  passwd = passwd + to64((int(ord(final[1])) << 16)
               |(int(ord(final[7])) << 8)
               |(int(ord(final[13]))), 4)

  passwd = passwd + to64((int(ord(final[2])) << 16)
               |(int(ord(final[8])) << 8)
               |(int(ord(final[14]))), 4)

  passwd = passwd + to64((int(ord(final[3])) << 16)
               |(int(ord(final[9])) << 8)
               |(int(ord(final[15]))), 4)

  passwd = passwd + to64((int(ord(final[4])) << 16)
               |(int(ord(final[10])) << 8)
               |(int(ord(final[5]))), 4)

  passwd = passwd + to64((int(ord(final[11]))), 2)
  
  return magic + salt + '$' + passwd


## assign a wrapper function:
md5crypt = unix_md5_crypt
#if __name__ == "__main__":
#  print unix_md5_crypt("cat", "hat")
   
  
    
      