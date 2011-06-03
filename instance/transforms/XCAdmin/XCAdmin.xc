
# Filename: XCAdmin.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

page div.login
doc
  success = transform (x.y.z) to call into spot occupying login box on success
rules
  #if they tried to login and failed, say that, else show status.
  py
    loginSuccessful = True  #flag for if the login and fail.
    if ARGS['logout']:  REQ.acl.logout()
    elif ARGS['login']: loginSuccessful = REQ.acl.login(ARGS['login'], ARGS['passwd'])
    
  print logged in as: [~REQ.acl.user~]  
  new form 
    set action [~THISURLREL~]login
    set method post
    new p
      text username:
      new input 
        set name login
        set type field
    new p
      text password:
      new input 
        set name passwd
        set type password
    new p
      new input
        set type submit
        set value Login
        
  new form 
    set action [~THISURLREL~]login
    set method post
    new input
      set type submit
      set name logout
      set value Logout
      
server div.userinit
  py REQ.acl.setDefaultShadow()
  text Users init'd
  
server div.status
  set style 
    float:right;
    margin: 5px;
    padding: 2px;
    background: #f4f4ff;
    font-family: arial;
    font-size: 1.4em;
  print
    XC Shell, Version 0.2.
    SessId: [~REQ.acl.sessid~]
    User: [~REQ.acl.user~]
    Groups: [~REQ.acl.getGroups()~]
    
    
server div.hithere group admin
  python
    if ARGS['yo']:
      something = ARGS['yo']
      LOCAL['something'].other = something
      
  text [~something~]
error
  text something not set
denied
  text sorry you cant
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  