
# Filename: ZloBase.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

define fragment.makeGroups
  pass

define fragment.makeParameters
  ? ARGV[1] != 'None'
    loop param in ARGV[1:]
      py 
        if '=' in param:
          name, value = [x.strip() for x in param.split('=')]
        else:
          name = param
          value = None
      new attribute 
        set name [~name~]
        set type [~ARGV[0]~]
        ? value is not None
          set value [~value~]
          
          
    