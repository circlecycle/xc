
# Filename: ZloACL.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

include ZloUI

start
  remotelink
    name: [~..listusers~]
    src: [~THISURLREL~]listusers

define view.interface
  valign 10
  
  view using adduser
  #view using removeuser
  #view using edituser
              
  smallGlassButton Refresh List
    onclick [~..listusers~]_send(null, null);
        
  ctxt white, Users in the system:
    fontsize 16
  
  replicate [~..listusers~]:/set  
    valign 5
    replicate user
      valign
      ctxt red, $path{'@name'}
      view
        x 20
        halign 5
        ctxt white, Groups:
        replicate groups
          ctxt 0xcdcdcd, $path{'@name'}
          
define view.adduser
  halign 10
  smallBarButton Add User
    middle
    oninit
      this.opened = false;
    onclick
      if(this.opened){
        parent.adduser.animate('width', 0, 300, false);
      }else{
        parent.adduser.animate('width', parent.adduser.fields.width, 300, false);
      }
      this.opened = !this.opened;
      
  clipview
    width 0
    name adduser
    horiz
      name fields
      edittext 
        name username
        set text (username)
      edittext 
        name password
        set password true
      edittext
        name groups
        set text (groups)
      smallGlassButton Add
        middle
        onclick
          return false;
          
define view.inspector
  margin 20
  roundbox
    fgcolor 0xdddddd
    opacity 0.5
  txt Inspect:
    center
    
server set.listusers group admin
  new user loop user in ROOT['acl'].spaces()
    set name [~user~]
    new groups loop group in ROOT['acl'][user].info['groups']
      set name [~group~]
      
server set.newuser group admin
  new user loop user in ROOT['acl'].spaces()
    set name [~user~]
    new groups loop group in ROOT['acl'][user].info['groups']
      set name [~group~]