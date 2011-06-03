
# Filename: ZloSite.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

include ZloUI

define view.zlo_interface
  ZloSite.ThreePaneLayout
    title: ThreePaneOne
    id: [~.master1~]
    security: admin
    belongs: [~.threepanetest1~]
    top:
      txt hi there
        centered
    
  ZloSite.Pane
    id: [~.panel11~]
    title: Pane One
    minimized: false 
    belongs: [~.threepanetest1~]
    contains:
      txt panel1
        centered
      
  ZloSite.Pane
    id: [~.panel12~]
    title: Pane Two
    belongs: [~.threepanetest1~]
    contains:
      txt panel2
        centered
      
  ZloSite.ThreePaneLayout
    title: ThreePaneTwo
    id: [~.master2~]
    belongs: [~.threepanetest2~]
    topcolor: 0xdddddd
    leftcolor: 0xffcccc
    bottomcolor: 0xddddf6
    top:
      txt hi there
        centered
    
  ZloSite.Pane
    id: [~.panel21~]
    title: Pane One
    minimized: false 
    belongs: [~.threepanetest2~]
    contains:   
      margin 20
      view using stores.zlo_interface
        clip
        fullsize
      
  ZloSite.Pane
    id: [~.panel22~]
    title: Pane Two
    belongs: [~.threepanetest2~]
    security: admin
    contains:
      margin 20
      view using browser.interface
        fullsize
        
    