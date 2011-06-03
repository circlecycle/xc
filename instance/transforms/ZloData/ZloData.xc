

# Filename: ZloData.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

include ZloBase, ZloWidgets

start
  py 
    securesets = []
    datasets = {}
    
  remoteset 
    name: [~..securityset~]
    src: [~THISURL~]security


finish
  #)Loading flag
  view
    id [~..loadingflag~]
    xywh 2, 3, 20, 20
    roundbox
      xy 1,1
      opacity 0.3
      fgcolor black
    roundbox
      fgcolor 0xAA4444    
    
  #)Setup the securesets master dataset. When the login changes, this is consulted to see which datasets need to be
  #)updated, and which ones should be reset.
  
  py
    #make a list from the the securesets collected, such that each group is a dict entry
    # equalling a list of datasets protected by that group.
    setsbygroup = {}
    for set in securesets:
      if setsbygroup.has_key(set['security']):
        setsbygroup[set['security']][set['name']] = True
      else:
        setsbygroup[set['security']] = {set['name']:True}
  
  init block
    new dataset set name [~..secureSets~]
      new group loop group in setsbygroup.keys()
        set name [~group~]
        new set loop set in setsbygroup[group].keys()
          set name [~set~]
          
  init block
    new dataset loop ds in datasets.keys()
      set name [~ds~]
      loop tag in datasets[ds]
        py 
          tagname = tag.keys()[0] ##only one named key in dict, that is, {tagname:{attributedict}}
          data = tag[tagname]
        new [~tagname~]
          attr data
    
define fragment.remoteset
doc
  make a new 
rules
  init block
    #?if there is a security attribute on this node, append it to a dictionary entry of it's name and restriction
    ? ATTR['security']
      py  
        securesets.append(
          {'name':      ATTR['name'], 
           'security':  ATTR['security']
          }
        )
      
    new dataset 
      set name [~ATTR['name']~]
      set src [~ATTR['src']~]
      set type http
      #?Specifing a link instead of a set only disables loading on the first call.
      test not ARGV['link']
        set request true
      on data
        [~..loadingflag~].animate('opacity', 0.00, 700, false);
        if([~ATTR['name']~]_response != false){
          [~ATTR['name']~]_response.execute();
        }
      
    init script tag
      var [~ATTR['name']~]_response = false;
      function [~ATTR['name']~]_send(obj, context, funcname){
        [~ATTR['name']~].setQueryString(null);
        [~ATTR['name']~].setQueryString(obj);
        if(context != null){
          [~ATTR['name']~]_response = new LzDelegate(context, funcname);
        }else{
          [~ATTR['name']~]_response = false;
        }
        [~ATTR['name']~].doRequest();
        [~..loadingflag~].setOpacity(1);
        [~..loadingflag~].animate('height', 20, 0, false);
      }
      
define fragment.classremoteset
doc
  make a new 
rules
  #?if there is a security attribute on this node, append it to a dictionary entry of it's name and restriction
  ? ATTR['security']
    py  
      securesets.append(
        {'name':      ATTR['name'], 
         'security':  ATTR['security']
        }
      )
      
  py name = ATTR['name']

  new dataset 
    set name [~name~]
    set src [~ATTR['src']~]
    set type http
    #?Specifing a link instead of a set only disables loading on the first call.
    ? not ARGV['link']
      set request true
    set ondata
      [~..loadingflag~].animate('opacity', 0.00, 700, false);
      [~ATTR['ondata']~]

  def [~name~]_send, obj
    [~name~].setQueryString(null);
    [~name~].setQueryString(obj);
    [~name~].doRequest();
    [~..loadingflag~].setOpacity(1);
    [~..loadingflag~].animate('height', 20, 0, false);
      
define fragment.DatasetGenerator
  python
    #nake the dictionary entry corresponding to dataset if nescessary
    name = ATTR['__dataset__']
    if not datasets.has_key(name):
      datasets[name] = []
  
    #get the attributes, making new dict with only data (metadata stripped and used here)
    elemdesc = dict([(x, TAG.getAttribute(x)) for x in TAG.attributes.keys()])
    entry = {}
    for key in elemdesc.keys():
      if key.startswith('_') or '.' in key: continue
      entry[key] = elemdesc[key]
        
    #append prepared entry for one element in a particular dataset!
    datasets[name].append({elemdesc['__elem__']:entry})
  
      
server security.security
doc
  this returns a dataset with the user's current groups
  for use in hiding laszlo components if they don't have
  authority to see them. 
rules
  ? ARGS['login']
    py
      if ARGS['login'] == '_LOGOUT': REQ.acl.logout()
      else:                          REQ.acl.login(ARGS['login'], ARGS['password'])
  new user set name [~REQ.acl.user~]
  new group loop entry in REQ.acl.getGroups()
    set name [~entry~]


eof
    
server security.registerUser
doc
  This will register a new user to the site and log them in under the new credential.
rules
  py
    REQ.acl.newUser(ARGS['user'], {'pw':ARGS['pw'], 'groups':['users'], 'meta':{}})
    REQ.acl.login(ARGS['user'], ARGS['pw'])
  new user set name [~REQ.acl.user~]
  new group loop entry in REQ.acl.getGroups()
    set name [~entry~]
    
    