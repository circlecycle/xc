
# Filename: FrozenSpace/Zope32.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#FrozenZopes! Works leveraging zope, can be adapted to other DB's. 
#my pride and joy. my great reward. 

import transaction
from xc import FrozenSpace

#only TRY to bring in zope interface. it's not necessary to have zope around if you're 
#just using the python API around your own app.. needed for the zope interface.
from zope.security.proxy import removeSecurityProxy
import zope.app.zapi

class New:
  def __init__(self, dbPath=None):
    pass
    
  def connect(self, app): 
    conn = Connection(app)
    return conn, conn.root()
     
  def close(self):      pass
  def pack(self):       pass
    

class Connection:
  def __init__(self, conn):
    self.conn = conn
    
  def root(self):  
    return FrozenSpace.FSpaceObj(Zope3DB(self.conn))
    
  def close(self):  pass
  def commit(self): pass
  def abort(self):  transaction.abort()
    
    
######## Zope3 Adapter #################### # # #  #   #    #
class Zope3DB:
  #these are normally on Space objects in the Zodb, so we don't list them.
  reservedFuncs = {
    'get':1, 'has_key':1, 'items':1, 'keys':1, 'name':1, 'values':1,
  }
  
  def __init__(self, app=None):
    self.app = app
   
  def keys(self, path):
    return [x for x in 
              dir(removeSecurityProxy(self.touch(path))) 
                if not x.startswith('_') 
                and not self.reservedFuncs.has_key(x)]
    
  def spaces(self, path):
    return [str(x[0]) for x in self.touch(path).items()]
    
  def has_key(self, path):
    obj = self.touch(path[:-1])
    if getattr(obj, path[-1], False) != False:  
      return True
    return False
    
  def has_space(self, path):
    obj = self.touch(path[:-1])
    if obj.get(path[-1], False) != False:
      return True
    return False
    
  def touch(self, path):
    #REMOVE 'REMOVE SECURITY PROXY' THINGY TO RENABLE ZOPE SECURITY - OFF FOR SESSIONCHECKER!
    obj = removeSecurityProxy(self.app)
    for name in path:
      try:    
        obj = obj[name]
      except: 
        obj[name] = zope.app.zapi.createObject('space.space.Space')
        obj = obj[name]
    return removeSecurityProxy(obj)
      
  def traverse(self, path, proxy=False):
    #REMOVE 'REMOVE SECURITY PROXY' THINGY TO RENABLE ZOPE SECURITY - OFF FOR SESSIONCHECKER!
    object = removeSecurityProxy(self.app)
    try:
      for name in path:
        object = object.get(name)
      if not proxy: return removeSecurityProxy(object)
      else:         
        return object
    except:
      return None
     
  def set(self, path, value=None):
    #touching first ensures the traverse works 
    object = removeSecurityProxy(self.touch(path[:-1]))
    container = self.touch(path[:-2])
    setattr(object, path[-1], value)    
    del container[path[-2]]    ##This commits the new objects!
    container[path[-2]] = object
    return object
    
  def get(self, path, default=None):
    return getattr(self.touch(path[:-1]), path[-1], default)

  def rmspace(self, path):
    try:
      self.touch(path)
      container = self.touch(path[:-1])
      del container[path[-1]]    ##This commits the new objects!
    except:
      return False
    return True
    
  def rm(self, path):
    try:
      container = self.touch(path[:-2])
      obj = container.get(path[-2])
      delattr(obj, path[-1])
      del container[path[-2]]
      container[path[-2]] = obj
    except:
      return False
    return True
      
  def copy(self, path, pathOfObj):
    try:
      container = self.touch(path)
      obj = self.traverse(pathOfObj)
      if container.has_key(pathOfObj[-1]):
        del container[pathOfObj[-1]]
      copier = zope.app.copypastemove.ObjectCopier(obj)
      copier.copyTo(container)
    except Exception, msg:
      return False
    return True

  
              