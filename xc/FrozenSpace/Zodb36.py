
# Filename: FrozenSpace/Zodb36.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

"""
Copyright (c) 2006, James Robey
All rights reserved.
"""

from ZODB import FileStorage, DB
from persistent.mapping import PersistentMapping
import transaction, copy

from xc import FrozenSpace, Config

setup = Config.setup

class New:
  def __init__(self, dbPath=setup.dbPath):
    self.db = DB(FileStorage.FileStorage(dbPath))
    
  def connect(self, app=None): 
    conn = Connection(self.db.open(), db=self.db)
    return conn, conn.root() 
    
  def close(self):      self.db.close()
  def pack(self):       self.db.pack()

class Connection:
  def __init__(self, conn, db=False):
    self.conn = conn
    self.db = db
    
  def root(self):  return FrozenSpace.FSpaceObj(Zodb36(self.conn.root()))
  def close(self):    self.conn.close()
  def pack(self):     self.db.pack()
  def commit(self):
    notcommitted = True
    while notcommitted:
      try:
        transaction.commit()
        notcommitted = False
      except:
        #ConflictError, do it again (gotta find that exception..)
        pass
        
  def abort(self):
    transaction.abort()
    

   
######## ZODB3.6 standalone Adapter #################### # # #  #   #    #
class Zodb36:  
  def __init__(self, app=None):
    self.commit = transaction.commit
    self.app = app
   
  def keys(self, path):
    obj = self.traverse(path)
    if obj:
      return [x for x in obj.keys() if not isinstance(obj[x], PersistentMapping) and x]
    else:
      return []
                
  def spaces(self, path):
    obj = self.traverse(path)
    if obj:
      return [x for x in obj.keys() if isinstance(obj[x], PersistentMapping) and x]
    else:
      return []
    
  def has_key(self, path):
    obj = self.traverse(path[:-1])
    if obj and obj.has_key(path[-1]) and not isinstance(obj[path[-1]], PersistentMapping):
      return True
    return False
    
  def has_space(self, path):
    obj = self.traverse(path[:-1])
    if obj and obj.has_key(path[-1]) and isinstance(obj[path[-1]], PersistentMapping):
      return True
    return False
    
  def touch(self, path):
    obj = self.app
    for name in path:
      if not obj.has_key(name): 
        obj[name] = PersistentMapping()
      obj = obj[name]
    return obj
      
  def traverse(self, path, proxy=False):
    obj = self.app
    try:
      for name in path:
        obj = obj[name]
      return obj
    except:
      return False
     
  def set(self, path, value=None):
    self.touch(path[:-1])[path[-1]] = value
    return object
    
  def get(self, path, default=None):
    try:    
      obj = self.traverse(path[:-1])[path[-1]]
      if obj: return obj
      else: return default
    except: return default

  def rmspace(self, path): 
    container = self.touch(path[:-1])
    #what if they erase the root object? just get rid of everything in app.
    if not path:
      for key in container.keys():
        del container[key]
    #normal erase
    elif container.has_key(path[-1]):
      if not isinstance(container[path[-1]], PersistentMapping):
        raise "rmspace passed an attribute instead of a space, when deleting", path
      del container[path[-1]]
    else:
      return False
    return True
    
  def rm(self, path):
    container = self.touch(path[:-1])
    if container.has_key(path[-1]) and isinstance(container[path[-1]], PersistentMapping):
      raise "rm passed a space instead of an attribute, when deleting", path
    elif container:
      del container[path[-1]]
      
  def copy(self, path, pathOfObj):
    if not isinstance(pathOfObj, list):
      raise "copy requires an FSpaceObj object or path list as argument, when copying", path
    try:  
      obj = self.traverse(pathOfObj)
      if obj:
        self.set(path+[pathOfObj[-1]], copy.deepcopy(obj))
      else: 
        raise "During copy, the object", `pathOfObj`, "doesn't exist"
    except:
      raise "During copy, the object", `pathOfObj`, "doesn't exist"
    

    
######## Tests #################### # # #  #   #    #
if __name__ == "__main__":
  import sys
  if len(sys.argv) > 1: filename = sys.argv[1]
  else: filename = 'fspace_test.db'
  print 'Opening a database at', filename
  print
  
  #Example, which, note, ends with nothing in it: We put stuff in one
  #by one, and take stuff out one by one, showing the different methods available
  
  db = New()
  conn = db.connect()
  root = conn[1]
  
  root.someattr = "Hello Word"
  root['spaceone'].one = "one"
  root['spaceone']['spacetwo'].two_a = "two_a"
  root['spaceone']['spacetwo'].two_b = "two_b"
  root['spaceone']['spacetwo'].set('two_c', 'two_c') 

  print root.has_key('someattr')
  print root.has_space('spaceone')
  print root.someattr
  print root.spaces()
  print root['spaceone'].one
  print root['spaceone']['spacetwo'].keys()
  print root['spaceone']['spacetwo'].get('two_b')

  del root['spaceone']['spacetwo'].two_a
  root['spaceone']['spacetwo'].rm('two_b')
  root['spaceone'].rmspace('spacetwo')
  root['spaceone'].empty()
  del root['spaceone']
  root.empty()
  
  print root.keys()
  
  conn[0].commit()
  conn[0].close()
  db.close()
  
  
