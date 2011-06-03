
# Filename: ZloEffects.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

include ZloBase 

define call.initTint
  #py raise "%s // %s - %s - %s - %s"%(ARGV, ARGV[0], ARGV[1], ARGV[2], ARGV[3])
  once
    py collectedTints = {}
  ? not collectedTints.has_key(ARGV[0])
    init script tag
      var [~ARGV[0]~] = new Object; 
      [~ARGV[0]~].rb = '[~ARGV[1]~]';
      [~ARGV[0]~].gb = '[~ARGV[2]~]';
      [~ARGV[0]~].bb = '[~ARGV[3]~]';
    py collectedTints[ARGV[0]] = True
  
      
define fragment.colorTransformRollover
doc
  generates: a rollover effect on the view it is called inside of.
  advertises: nothing
  expects: [~ARGV[0]~], [~ARGV[1]~], [~ARGV[2]~] to be r,g,b values
  demo:
    n fragment u ZloBase.colorTransformRollover <required red amt>, <required green amt>, <required blue amt>
rules
  initTint [~..NoTint~], 0,0,0
  py key = "%s%s%s"%(ARGV[0], ARGV[1], ARGV[2])
  initTint tint[~key~], [~ARGV[0]~], [~ARGV[1]~], [~ARGV[2]~]
  event onmouseover
    this.setColorTransform(tint[~key~]);
  event onmouseout
    this.setColorTransform([~..NoTint~]);
    
    
define fragment.draggable
  py 
    if ARGV != 'true': name = ARGV
    else:              name = AUTO
  drag [~name~]
  event onmousedown
    [~name~].apply();
    this.parent.bringToFront();
  event onmouseup
    [~name~].remove();
    
define fragment.animate_gen
  t this.animate('[~ARGV[0]~]', '[~ARGV[1]~]', '[~ARGV[2]~]', false);
    