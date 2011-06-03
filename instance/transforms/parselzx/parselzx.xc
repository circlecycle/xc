
include ZloUI

#)CLIENT SIDE TRANSFORMS

start
  #gets the recent paths list
  remoteset
    name: [~..history~]
    src: [~THISURLREL~]history
    
  #action to clear the history
  remotelink
    name: [~..clear~]
    src: [~THISURLREL~]clear
    
  #makes one window that loads a parsed file and updates history
  Object [~..onepage~], window
    string path
    string fromhistory
    
    #set window attributes
    set resizable true
    set closeable true
    wh 480, 640
    clip
    bgcolor 0xcccccc
    
    #load the path pointed to in the class attributes on instantiation
    classremoteset
      name: parsedfile
      src: [~THISURLREL~]parsetree
      initargs:
        obj.path = this.getAttribute('path');
        obj.fromhistory = this.getAttribute('fromhistory');
      ondata:
        [~..history~]_send(null, null);
          
    #a view with a scrollbar to contain the listing
    vert
      #local dataset has the info on how to paint the results:
      replicate local:classroot.parsedfile:/set/entry
        clip
        waypoint
        #highlight and action per replication
        blueRollover
          on init
            this.opened = false;
          on click
            if(!this.opened){
              parent._.info.animate('height', parent._.info.height, 200, true);
              parent._.info.animate('height', parent._.info.height, 200, true);
            }else{
              parent.animate('height', -parent._.info.height, 200, true);
            }
            this.opened = !this.opened
        
        #display per replication
        vert
          x $path{'@indent'}
          #element description line
          horiz
            txt $path{'@type'}
            txt $path{'@names'}
              bgcolor 0xccccde
              selectable
              
          #extended info area (code, notes)
          view
            height 0
            txt $path{'text()'}
              bgcolor 0xe4e4e4
              wof classroot
              waypoint info
              multiline
              selectable
    scroll y
      

define view.main
  ZloUI.INIT
  #Window
  #  id: [~.test~]
      
  Window
    id: [~.window~]
    title: parselzx
    wh: 480, 640
    contains:
      valign
      fullsize
  
      #params for new windows
      horiz 20
        name params
        new edittext set text LZX Code
          width 300
          name path
          selectable
        smallGlassButton Submit
          name submit
          middle
          onclick new [~..onepage~]([~..container~], {path:parent.path.getText()})
        smallGlassButton Clear History
          middle
          on click
            [~..clear~]_send(null, this, 'response');
          def response
            [~..history~]_send(null, null);
    
      #main area
      view
        clip
        wof parent
        hofminus parent, parent.params.height
        clip
        #path history display
        vert
          replicate [~..history~]:/set/entry
            blueRollover
              onclick new [~..onepage~]([~..container~], {path:parent.datapath.getNodeText(), fromhistory:'yes'});
            txt $path{'text()'}
        
    #home of application windows
    Desktop
      id: [~.dekstop~] 
      title: parselzx windows
      minimized: false
      contains:
        viewid [~..container~] 
   
#) SERVER SIDE TRANSFORMS
   
server set.clear
  python
    LOCAL['history'].empty()
    
server set.history
  python 
    history = LOCAL['history'].keys()
    history.sort()
  new entry loop key in history
    text [~LOCAL['history'].get(key)~]
  
server set.parsetree
init
  import os.path, time
  from xml.dom.minidom import parseString
  
  Object parseLZX:
    def __init__(self, fname):
      self.indent = 4
      self.output = []
      root = parseString(open(fname).read()).documentElement
      self.walk(root)

    def walk(self, root):  
      for node in [x for x in root.childNodes if x.nodeType == x.ELEMENT_NODE]:
        id = node.getAttribute('id')       
        name = node.getAttribute('name')
        event = node.getAttribute('event')
        if not (event or id or name):
          continue
                                                                         
        names = "%s:%s:%s"%(id, name, event)
        nodetext = ""
        if node.tagName.lower() in ('method', 'event', 'handler'):
          if node.firstChild:
            node.normalize()
            nodetext = node.firstChild.nodeValue
          else:
            nodetext = "[[no text]]"
        else:
          nodetext = node.toxml()
          
        self.output.append([self.indent, node.tagName.upper(), names, nodetext])
        self.indent += 4   
        self.walk(node)
        self.indent -= 4
        
rules
  python
    if not ARGS['path']:
      output = False
    elif not os.path.exists(ARGS['path']):
      output = False
    else:
      output = parseLZX(ARGS['path']).output
      if ARGS['fromhistory'] != 'yes':
        LOCAL['history'].set(time.time(), ARGS['path'])
      
  ? output
    #parse and xmlify the buffer:
    new entry loop entry in output
      set indent [~entry[0]*5~]
      set type [~entry[1]~]
      set names [~entry[2]~]
      text [~entry[3]~]
  e.
    #or give a file not found message
    new entry
      set indent 0
      set type No file
      set names specified
      text nothing loaded
  
