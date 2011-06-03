
# Filename: FrozenSpace/__init__.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

##modulify

from xc import Config
import copy

######## FSpaceObj: the tree creation mechanism #################### # # #  #   #    #
class FSpaceObj:
  rootname = Config.setup.dbRootName
  
  def __init__(self, db, basepath=[rootname]):
    self.db_ = db  
    self.basepath_ = basepath

  #return the path to the object joined
  def __str__(self):
    if len(self.basepath_) > 1:
      return '/'.join(self.basepath_[1:])
    else:
      return ''
    
  #return the path to the object as python list represtation
  def __repr__(self): 
    if len(self.basepath_) > 1:
      return '/'.join(self.basepath_[1:])
    else:
      return ''
    
  def __call__(self):
    if len(self.basepath_) > 1:
      return self.basepath_[1:]
    else:
      return []
    
  #return the number of items the FSpaceObj contains (folders)
  def __len__(self):
    return len(self.db_.keys(self.basepath_))
  
  #if a FSpaceObj object exists with the requested name return it, otherwise return a new FSpaceObj with that name.
  def __getitem__(self, key):
    if not self.__dict__.has_key(key):   
      self.__dict__[key] = FSpaceObj(self.db_, basepath=self.basepath_+[key])
    return self.__dict__[key]
      
  #You can't assign to a FSpaceObj object, but you CAN assign to an attribute inside of one aka F = True is bad, F.a = true is good.
  def __setitem__(self, key, value):
    raise "Can't assign to a FrozenSpace object: %s[%s]" % (self.basepath, key)
    
  #delete an FSpaceObj object using the 'del syntax'
  def __delitem__(self, key):
    return self.db_.rmspace(self.basepath_+[key])
    
  #delete a contained attribute using the 'del syntax'
  def __delattr__(self, key):
    if key.endswith('_'):     del self.__dict__[key]
    else:                     return self.db_.rm(self.basepath_+[key])
    
  #return an attribute of a given name, None if not there
  def __getattr__(self, key):
    return self.db_.get(self.basepath_+[key], default=None)
        
  #set an attribute of a given name UNLESS an FSpaceObj of that name already exists, except if so.
  def __setattr__(self, key, value):
    if key.endswith('_'):   
      self.__dict__[key] = value
    else:
      self.db_.set(self.basepath_+[key], value)  
      
  def goto(self, gotopath):
    if type(gotopath) == type(''):
      gotopath = gotopath.split('/')
    return FSpaceObj(self.db_, basepath=self.basepath_+gotopath)
  
  #if the name given to this doesn't exist inside of the FSpaceObj object, create a new FSpaceObj object there
  def touch(self, key):
    if self.db_.touch(self.basepath_+[key]): 
      return self[key]
    else:
      return False
      
  #reset, clear, empty, what-have-you an FSpaceObj object such that it now exists with no attributes inside
  def empty(self):
    self.db_.rmspace(self.basepath_)
    self.db_.touch(self.basepath_)
    return self
    
  #test if a given item OR folder is inside of an FSpaceObj
  def has_key(self, key):
    return self.db_.has_key(self.basepath_+[key])
    
  def has_space(self, key):
    return self.db_.has_space(self.basepath_+[key])
  
  #return the names of the attributes the FSpaceObj contains
  def keys(self):
    return self.db_.keys(self.basepath_)
    
  #return the names of the folders the FSpaceObj contains
  def spaces(self):
    self.db_.touch(self.basepath_)
    return self.db_.spaces(self.basepath_)
    
  #set a given attribute on an FSpaceObj object
  def set(self, key, value):
    return self.db_.set(self.basepath_+[key], value)
    
  #get a given attribute value or FSpaceObj object from an FSpaceObj object
  def get(self, key, default=None):
    return self.db_.get(self.basepath_+[key], default=default)
    
  def rm(self, key):
    return self.db_.rm(self.basepath_+[key])
    
  def rmspace(self, key):
    return self.db_.rmspace(self.basepath_+[key])
    
  #given another FSpaceObj object, copy that object into this FSpaceObj object
  def copy(self, copyObj):
    self.db_.touch(self.basepath_)
    return self.db_.copy(self.basepath_, copyObj.basepath_)
   