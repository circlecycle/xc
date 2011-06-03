
include ZloBase, ZloEffects

define view.main
  fullsize
  bgcolor 0xddddff
  xml <text bgcolor="red" valign="middle" text="hi there"/>
  new text set id [~.output~]
    fullsize
    def append, buf
      this.setText(this.getText() + buf);
  new view using qwerty [~.output~], 60, 60
    centered
    
define view.qwerty
  valign 20
  fontsize 40
  center
  py rows = ['.,!?:;\"()', "qwertyuiop", "asdfghjkl", "zxcvbnm", ' ' ]
  loop row in rows
    new view
      center
      halign 10
      loop letter in row
        KeyboardKey
          fieldid: [~ARGV[0]~]
          letter: [~letter~]
          wh: [~ARGV[1]~], [~ARGV[2]~] 


  

