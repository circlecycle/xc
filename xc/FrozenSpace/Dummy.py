
# Filename: FrozenSpace/Dummy.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

from xc import FrozenSpace, Config

#!-----------------------------
#!Doesn't work, out of date
#!But could be fixed easily!
#!-----------------------------

setup = Config.setup

class New:
  def __init__(self, dbPath=None):
    pass
    
  def connect(self, app=None):    
    root = Connection(Dodb())
    return root, root.root()
    
  def close(self):      pass
  def pack(self):       pass

class Connection:
  def __init__(self, conn):
    self.conn = conn
  def root(self):  return FrozenSpace.FSpaceObj(DummyDB(self.conn))
  def close(self): pass
  def commit(self):     pass
  def abort(self):      pass
    

######## Dummy Object Database Object (Dodb) #################### # # #  #   #    #
class Dodb:
  """Dumb object database :)"""
  def get(self, key):         return getattr(self, key, None)
  def set(self, key, value):  return setattr(self, key, value)


######## Dodb Adapter #################### # # #  #   #    #
class DummyDB:
  def __init__(self, app=Dodb()):
    self.app = app
    self.root = setup.dbRootName
    
  def keys(self, path):
    return dir(self.traverse(path))
    
  def spaces(self, path):
    obj = self.traverse(path)
    return [str(x[0]) for x in dir(obj) if self.isdir(getattr(obj, x, None))]
    
  def has_key(self, path):
    object = self.traverse(path[:-1])
    if object.get(path[-1]):   return True
    else:                      return False
      
  def has_space(self, path):
    object = self.traverse(path[:-1])
    if object.get(path[-1]):   return True
    else:                      return False
    
  def touch(self, path):
    object = self.app
    for name in path:
      tmp = object.get(name)
      if tmp == None:
        setattr(object, name, Dodb())
        object = object.get(name)
      else:
        object = tmp
    
  def traverse(self, path):
    object = self.app
    try:
      for name in path:
        object = object.get(name)
      return object
    except:
      return None
     
  def set(self, path, value=None):
    self.touch(path[:-1])
    container = self.traverse(path[:-2])
    object = container.get(path[-2])
    return setattr(object, path[-1], value)
    
  def get(self, path, default=None):
    return getattr(self.traverse(path[:-1]), path[-1], default)
    
  def getObj(self, path, default=None):
    return getattr(self.traverse(path[:-1]), path[-1], default)
    
  def copy(self, path, pathOfObj):
    container = self.traverse(path)
    copiedObj = self.traverse(pathOfObj)
    return setattr(container, pathOfObj[-1], copiedObj)
    
  def rm(self, path):
    container = self.traverse(path[:-2])
    object = container.get(path[-2])
    del container[path[-1]]    ##This commits the new objects!
    
  def rmspace(self, path):
    self.rm(path)