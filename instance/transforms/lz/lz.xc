
# Filename: lz.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

stateless
  
#TODO: ARGP not happy with noexc version   
page div.run
  new object using [~ARGP[0]~] %% width='100%', height='100%'
  
laszlo parselzx
  debug
  new view using parselzx.main
  
laszlo touch
  debug
  new view using ZloTouch.main

laszlo waypoint
  debug 
  new view using ZloTest.testwp