
# Filename: Identity.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

from Utils import dbug_func as dbug
from Utils import intersect
from xc import Config
import shelve, os

setup = Config.setup

#one of these per request.
#fundamentally this is tied into the SessionHandler, which is relied on to return credentials.
#the session is estabilshed before the ACL, but it is then wrapped here to provide easier
#access from an API perspective.

class IdentityManager:
  shadowDefault = {
    "anonymous":    {'pw':'', 'groups':['anonymous'], 'meta':{}},
    "jamesr":       {'pw':'letmego2', 'groups':['anonymous', 'users', 'admin'], 'meta':{}},
    "admin":        {'pw':'letmego2', 'groups':['anonymous', 'users', 'admin'], 'meta':{}},
    "bob":          {'pw':'letmein', 'groups':['anonymous', 'users', 'bobsgroup'], 'meta':{}},
    "ted":          {'pw':'letmein', 'groups':['anonymous', 'users',], 'meta':{}},
  }
    
  def __init__(self, req, zodb):
    global setup
    #this is the session handler from the adapters.apache2 module
    self.sessionHandler = req.sessionHandler
    self.aclSpace = zodb['acl']
    self.refreshState()
    
  def refreshState(self):
    self.user = self.sessionHandler.user
    self.sessid = self.sessionHandler.sessid
    
    #is anonymous? set a flag.
    if self.user == self.sessionHandler.unauthorized:  
      self.anonymous = True
    else:                                     
      self.anonymous = False
    
    #set up what user we are (load from the zodb)
    self.info = self.aclSpace[self.user].info
    
    #if the user doesn't have an entry, make an empty one.
    if not self.info:
      self.aclSpace[self.user].info = {'pw':'', 'groups':[self.sessionHandler.unauthorized]}
      self.info = self.aclSpace[self.user].info
      
  #these reach into the session machinery
  def login(self, newuser, pw):
    if self.aclSpace.has_space(newuser):
      if self.aclSpace[newuser].info['pw'] == pw:
        #change the in memory session to reflect the new status.
        self.sessionHandler.login(user=newuser)
        #since we changed things, refresh.
        self.refreshState()
        return True
    return False
  
  def logout(self, sessid=False):
    #by specifiying a session id anyone can be logged out, and
    #if it happens to be the current user then it's a logout like normal.
    if sessid:  self.sessionHandler.logout(sessid=sessid)
    else:       self.sessionHandler.logout()
    #and refresh the state of attributes for inspection by other modules
    self.refreshState()
    
  #these get information on group status
  def getGroups(self):   
    return self.info['groups']
    
  def isInGroup(self, group):
    if intersect(group, self.info['groups']):
      return True
    return False
    
  def addToGroup(self, group):
    if group not in self.info['groups']:
      self.info['groups'].append(group)
      self.user.info = self.info
      
  def removeFromGroup(self, group):
    if group in self.info['groups']:
      del self.info['groups'][self.info['groups'].index(group)]
      self.user.info = self.info
      
  #These are used for the management of the users
  def setDefaultShadow(self):
    """use me to initialize a zodb from above dict - run just once, usually, or for debugging."""
    for user in self.shadowDefault.keys():
      if not self.aclSpace.has_key(user):
        self.aclSpace[user].info = self.shadowDefault[user]
      
  def getUsers(self):    
    return self.aclSpace.spaces()  
    
  def getGroupsFor(self, user):
    if self.aclSpace.has_space(user):
      return self.aclSpace[user].info['groups']
    else:
      return []
    
  def isUserInGroup(self, user, groups):
    if intersect(groups, self.aclSpace[user]['groups']):
      return True
    return False
    
  def addUserToGroup(self, user, group):
    info = self.aclSpace[user].info
    if group not in info['groups']:  
      del info['groups'][info['groups'].index(group)]
      self.aclSpace[user].info = info
      
  def removeUserFromGroup(self, user, group):
    info = self.aclSpace[user].info
    if group in info['groups']:  
      info['groups'].append(group)
      self.aclSpace[user].info = info
      
  #make a new user
  def newUser(self, user, info=False):
    if not self.aclSpace.has_space(user):
      if not info:
        self.aclSpace[user] = {'pw':False, 'groups':[], 'meta':{}}
      else:
        self.aclSpace[user] = info
        
  def removeUser(self, user):
    if self.aclSpace.has_space(user):
      del self.aclSpace[user]

    
