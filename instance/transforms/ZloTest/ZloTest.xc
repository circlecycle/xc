
# Filename: ZloTest.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

include ZloUI

start
  dataset [~..dropdown1~]
    loop i in range(20)
      entry Choice [~i~]
      
define view.testwp
  Object [~.test~]
    id testme
    waypoint
    view
      view
        view
          bgcolor red
          waypoint colors
    on init
      Debug.write(this._.colors);
  
  new [~.test~]
      
define view.zlo_interface
  ZloUI.Desktop
    id: [~.desktop1~]
    title: Desktop Test
    contains:
      roundbox
        fgcolor 0xdddddd
        opacity 0.8
      txt hi there

  ZloUI.Window
    id: [~.winone~]
    title: Widgets and Testing
    wh: 240, 320
    xy: 140, 340
    contains:
      view
        valign 10
        bigGlassButton Big Button
        smallGlassButton Small Button
        txt Nothing
          name field
        ZloWidgets.aquaDropdown 
          id: [~.dropone~]
          path: [~..dropdown1~]:/entry
          elem: @data 
          initial: Choose... 
          doAfter:
            parent.field.setText(this.value);
            
  ZloUI.Window
    id: [~.testwin~]
    title: Testing Window
    xy: 200, 200
    wh: 450, 200
    contains:
      bgcolor black
      valign
      clipview
        name content
        fullsize
        view
          name inner
          valign
          fgcolor white
          loop entry in range(20)
            txt Yo there [~entry~]
        scroll
          on height
            if(parent.height > parent.inner.height) this.setVisible(false);
            else this.setVisible(true);
            
      
define view.dynamicLoading    
  ZloUI.INIT
  
  ZloData.remotelink
    name: [~.myset~]
    src: [~THISURLREL~]testdata
    
  ZloUI.Window
    id: [~.winone~]
    title: dynamic loading test
    wh: 240, 420
    xy: 140, 340
    contains:
      valign 10
  
      txt Show View
        onclick parent.content.setVisible(true);
    
      txt Hide View
        onclick parent.content.setVisible(false);
    
      ZloData.DataLoadingView 
        dataset: [~.myset~]
        name content
        wof parent
        bgcolor 0xddddff
        valign
        replicate [~.myset~]:/set/entry
          txt $path{'text()'}
          
define fragment.testUserWindow
  ZloUI.Window
    id: [~.bobswin~]
    security: users
    title: User's window
    wh: 200, 200
    xy: 100, 100
    minimized: true
    contains:
      valign 10
      new text
        wof parent
        multiline
        text
          Just a demo only logged in users
          can see this message. Try logging out
          to see how things to see how things are
          protected.
      
server set.testdata
init
  import time
rules
  new entry text Time is:
  new entry text [~time.time()~]
  new entry text Done.
  
             

  
