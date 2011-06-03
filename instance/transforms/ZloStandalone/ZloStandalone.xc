

define view.fielderror
  init block
    Object [~..wtfielderror~]
      string textmsg
      number textx
      bool wasCorrectState, false

      def error
        this.setAttribute('wasCorrectState', false);
        this.box.setAttribute('bgcolor', '0xFF0000');
        this.box.animate('width', this.width, 500, false, {motion:'easein'});
        this.invalidemail.setVisible(true);

      def close
        this.setAttribute('wasCorrectState', false);
        this.box.animate('width', 0, 500, false, {motion:'easeout'});
        this.invalidemail.setVisible(false);

      def correct
        this.setAttribute('wasCorrectState', true);
        this.box.setAttribute('bgcolor', '0x00FF00');
        this.invalidemail.setVisible(false);

      def wascorrect
        this.setAttribute('wascorrect', false);
        return this.getAttribute('wasCorrectState');

      on width
        Debug.write('width:', this.box);
        if(this.box.getAttribute('width') != 0){
            this.box.setAttribute('width', this.getAttribute('width'));
        }

      on height
        if(this.box.getAttribute('height') != 0){
            this.box.setAttribute('height', this.getAttribute('height'));
        }

      viewname box
        wh 0, ${classroot.getAttribute('height')}

      txt ${classroot.getAttribute('textmsg')}
        name invalidemail
        x ${classroot.getAttribute('textx')}
        visible false
        middle
        fgcolor red
        fontstyle bold
      
  valign 20
  
  view
    edittext nothin special
      name nothinfield
      width 200
      on keyup
        Debug.write('keyup on nothin special')
      
  view
    new [~..wtfielderror~]
      name errorbox
      xywh -1, -1, 202, 102
      set textmsg Invalid
      set textx 300
    
    edittext Validate Me
      name emailfield
      width 200
    
      on blur
        Debug.write('blur');
        (parent.isValid(this.value) || !this.value) ? 
          parent.errorbox.close() : 
          parent.errorbox.error();
    
      on keyup
        Debug.write('keyup');
        (parent.isValid(this.value) || !this.value) ? 
            parent.errorbox.correct() : 
            (parent.errorbox.wascorrect()) ?
              parent.errorbox.error() : 
              false;

    def isValid, what
      return (what == 'yothere') ? true :  false;
      
    
      
    
