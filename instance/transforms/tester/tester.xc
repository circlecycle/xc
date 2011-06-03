
# Filename: tester.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

include XCStubs, ZloBase
skin tester

page div.index
  show Start..
    
  print subslot tests
  subslot
    test::
      one: hello
      two: there
    me: world
    
  print multiple line removal test
  multioptional
    text: Hi There
    style:
      border: 1px solid red;
      color: blue;
      
  print ---
    
  print optional inclusion test  
  optional
    color: blue
    text: hi there
    morerules:
      text yodude
  optional
    text: hi there
      
  print moved items
  moveStub movetest
  
  collectionStub TestStub
  
  print ----
  param one, two, three
  print break ----
  param
  print break ----
  shell
  print break ----
  shell
    make: 27, 9, 3
    content: text overridden
  print ----
  
  markForMove movetest
    new div
      set style color: red
      text redmove
      
  markForMove movetest
    new div
      set style color: green
      text greenmove
      
  markForMove movetest
    new div
      set style color: blue
      text bluemove
  
  show Demo Over
  
finish
  targetStub TestStub, b
  
  print Stub Test

  