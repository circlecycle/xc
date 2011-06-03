
# Filename: Parser_Setup.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#################### # # #  #   #    #
# THIS sets up the type of transform we recognize in the parser. Much simpler then most parser. But it's 
# only gotta be done once at server start, so the relative ease was important to me.
# it works by classiying what recognized transforms' id belongs to what type of transform.
# they are then handled in the rest of the engine in generic ways. 
# so for instance, if a transform type is not in restrictedTransforms, then it won't be checked for auth info
# before running.
#################### # # #  #   #    #
    

primaryTransforms = [
  'filterRestricted', 'filter', 'filterall', 'defineRestricted',
  'define', 'reqstart', 'reqend', 'server', 'serverPage',
  'serverRestricted', 'inheritAlias',
  'inheritFilter', 'inheritDefine', 'inheritServer', 'preheritFilter', 'preheritDefine', 'preheritServer',
  'inheritFilterRestricted','inheritDefineRestricted', 'inheritServerRestricted', 'preheritFilterRestricted',
  'preheritDefineRestricted', 'preheritServerRestricted', 'EOF', 'stateful', 'stateless', 'group',
  'preheritLaszloRestricted', 'inheritLaszloRestricted', 'preheritLaszlo', 'inheritLaszlo', 'laszloRestricted',
  'laszlo', 'include', 'shell', 'skin'
]

normalCaughtTransforms = [
  'filter', 'filterall', 'filterRestricted', 'server', 'serverRestricted', 'serverPage', 
  'laszlo', 'laszloRestricted'
]

allCaughtTransforms = [
  'filter', 'filterall', 'filterRestricted', 'server', 'serverRestricted', 
  'define', 'defineRestricted', 'serverPage', 'laszlo', 'laszloRestricted', 'shell'
]

secondaryTransforms = [
  'error', 'denied', 'document', 'initspace', 'default'
]

restrictedTransforms = [
  'filterRestricted', 'serverRestricted', 'defineRestricted', 'inheritFilterRestricted',
  'inheritDefineRestricted', 'inheritServerRestricted', 'preheritFilterRestricted',
  'preheritDefineRestricted', 'preheritServerRestricted', 'wrapsDefineRestricted', 'laszloRestricted',
  'preheritLaszloRestricted', 'inheritLaszloRestricted'
]
                         
textSecondaryTransforms = [
  'document', 'initspace', 'default'
]

transformsWithoutAttrToRemove = [
  'filterall', 'reqstart', 'reqend', 'EOF', 'stateful', 'stateless', 'group', 'include'
]

scriptingTransforms = [
  'startwrap', 'startwrapusing', 'startwrapxml', 'startwraptext', 'startwrapset', 
  'startwrapattr', 'loopusing', 'loop', 'if'
]


transformConfig = {   
  ('filter', None, 'before', None, 'group', False)  :'preheritFilterRestricted',
  ('filter', None, 'after', None, 'group', False)   :'inheritFilterRestricted',
  ('filter', None, 'before', None, False)           :'preheritFilter',
  ('filter', None, 'after', None, False)            :'inheritFilter',
  ('filter', None, 'group', False)                  :'filterRestricted',
  ('filter', None, False)                           :'filter',
  
  ('define', None, 'before', None, 'group', False)  :'preheritDefineRestricted',
  ('define', None, 'after', None, 'group', False)   :'inheritDefineRestricted',
  ('define', None, 'before', None, False)           :'preheritDefine',
  ('define', None, 'after', None, False)            :'inheritDefine',
  ('define', None, 'group', False)                  :'defineRestricted',
  ('define', None, False)                           :'define',
  
  ('server', None, 'before', None, 'group', False)  :'preheritServerRestricted',
  ('server', None, 'after', None, 'group', False)   :'inheritServerRestricted',
  ('server', None, 'before', None, False)           :'preheritServer', 
  ('server', None, 'after', None, False)            :'inheritServer',   
  ('server', None, 'group', False)                  :'serverRestricted',
  ('server', None, False)                           :'server',
  
  #finish syntax hightlight
  ('laszlo', None, 'before', None, 'group', False)  :'preheritLaszloRestricted',
  ('laszlo', None, 'after', None, 'group', False)   :'inheritLaszloRestricted',
  ('laszlo', None, 'before', None, False)           :'preheritLaszlo',
  ('laszlo', None, 'after', None, False)            :'inheritLaszlo',
  ('laszlo', None, 'group', False)                  :'laszloRestricted',
  ('laszlo', None, False)                           :'laszlo',
  
  ('shell', None, 'uses', None, False)              :'shell',
  
  ('page', None, 'uses', False)                     :'serverPage',
  ('page', None, False)                             :'serverPage',
  
  ('alias', None, 'from', None, False)              :'inheritAlias',
  
  ('start', False)                                  :'reqstart',
  ('finish', False)                                 :'reqend',
  ('default', False)                                :'default',
  ('error', False)                                  :'error',
  ('doc', False)                                    :'document',
  ('denied', False)                                 :'denied',
  ('rules', False)                                  :'rules',
  ('init', False)                                   :'initspace',
  ('stateful', False)                               :'stateful',
  ('stateless', False)                              :'stateless',
  ('group', True)                                   :'group',
  ('include', True)                                 :'include',
  ('skin', True)                                    :'skin',
  ('eof', False)                                    :'EOF', 
}

#    IMPORTANT!! this defines the syntax of the commands (rules) and the keyword
#    that assoicates it with the right action in the processor. With this, you can 
#    add new commands just by adding a new entry! the None entries denote parameters
#    that are to be grabbed as arguments, while True or False at the end indicates 
#    whether there may also be a text block that will be saved and passed as well.
#    you can then add a new processing directive (uh, if test anyone?:) in the processor.py 
#    module (which is always pre-loaded with the current tag under the microscope)
#    and boogie right along.

    
fullTextRules = ['python', 'xml', 'text', 'insert', 'init', 'initbottom', 
    'print', 'startwrapprint', 'startwraptext']
escapedRules = ['text', 'init', 'print', 'startwrapprint', 'startwraptext']
checkxml = ['addxml', 'insertxml']
checkpython = ['python']

rulesWithScope = {
  'startwrap'             :'endwrap',
  'startwrapins'          :'endwrapinsert',
  'startwrapusing'        :'endwrap',
  'startwrapinsusing'     :'endwrapinsert',
  'startwrapxml'          :'endwrap',
  'startwrapxmlins'       :'endwrapinsert',
  'startwraptext'         :'endwrap',
  'startwraptextins'      :'endwrapinsert',
  'startwrapset'          :'endwrap',
  'startwrapsetins'       :'endwrapinsert',
  'startwrapattr'         :'endwrap',
  'startwrapinitbottom'   :'initbottomwrap',
  'startwrapinitunique'   :'inituniquewrap',
  'startwrapinituniqueon' :'inituniquewrap',
  'startwrapinit'         :'initwrap',
  'if'                    :'endif',
  'elif'                  :'endif',
  'else'                  :'endif',
  'loop'                  :'endloop',
  'loopusing'             :'endloop',}

rulesWithSnapback = ['if', 'else', 'elif', 'startwrapinitunique', 'startwrapinituniqueon']

#Two syntaxs are defined side by side that are equivelant except for shorter key sequences
#to be used when familar with all the commands.
ruleConfig = {                    
  ('remove', True)                    :'remove', 
  ('-', True)                         :'remove',
                                       
  ('set', None, True)                 :'setattr', 
  ('=', None, True)                   :'setattr',
                                      
  ('prepend', None, True)             :'prepend', 
  ('+', None, True)                   :'prepend',
                                      
  ('append', None, True)              :'append', 
  ('>', None, True)                   :'append',
                                      
  ('attr', True)                      :'attr', 
  ('*', True)                         :'attr',
        
  ('init', 'block', 'once', 'on', None, False):'startwrapinituniqueon', 
    ('init', 'block', 'below', False)   :'startwrapinitbottom', 
    ('init', 'block', 'once', False)    :'startwrapinitunique', 
    ('init', 'block', False)            :'startwrapinit',    
    ('init', None, 'tag', 'below', True):'initbottom',                             
    ('init', None, 'tag', 'once', True) :'initunique', 
    ('init', None, 'tag', True)         :'init',  
    #it's final form is at the bottom.
                                  
  ('load', None, True)                :'loadunique', 
  ('ld', None, True)                  :'loadunique',
                                      
  ('include', True)                   :'import', 
                                      
  ('xml', True)                       :'addxml', 
  ('html', True)                      :'addxml', 
  #('x', True)                         :'addxml',
                                      
  ('insert', 'xml', True)             :'insertxml', 
  ('i', 'x', True)                    :'insertxml',
                                      
  ('clear', False)                    :'erase', 
                                      
  ('return', False)                   :'return',
  
  ('context', 'now', True)            :'context',

  ('contents', 'into', None, False)   :'read', 
                                      
  ('print', True)                     :'print',
  ('p', True)                         :'print',  
                                      
  ('text', True )                     :'addtext', 
  ('t', True)                         :'addtext',
  
  ('binary', True )                   :'binary', 
                                      
  ('insert', 'text', True)            :'inserttext', 
  ('i', 't', True)                    :'inserttext',
                                      
  ('python', True)                    :'python', 
  ('py', True)                        :'python',
  
  ('eval', None, True)                :'evaluate',
  ('evaluate', None, True)            :'evaluate',
                                      
  ('call', None, False)               :'call', 
  ('call', None, True)                :'call',
                            
  ('new', None, 'loop', None, 'in', True):'loopusing', 
  ('n', None, 'loop', None, 'in', True):'loopusing', 
  ('new', None, 'for', None, 'in', True):'loopusing', 
  ('n', None, 'for', None, 'in', True):'loopusing', 
  
  #a number of variations on the useful 'new' keyword to make new elements in the DOM.
    
  #having two versions with text blocks on and off disambiguates when a user wishes to have 
  #inner commands or not. useful in that we can have one liners' "for free".
  ('insert', 'new', None, 'using', None, False):'startwrapinsusing',
  ('i', 'n', None, 'u', None, False)  :'startwrapinsusing',

      ('insert', 'new', None, 'using', None, True):'startwrapinsusing',
      ('i', 'n', None, 'u', None, True)   :'startwrapinsusing',

      #
                                          
      ('new', None, 'using', None, False)   :'startwrapusing', 
      ('n', None, 'u', None, False)         :'startwrapusing',
                                          
      ('new', None, 'using', None, True)    :'startwrapusing', 
      ('n', None, 'u', None, True)          :'startwrapusing',
                                          
      #this one same as above but passes one multiline text block only.
      ('new', None, 'args', None, True)     :'startwrapusing', 
      ('n', None, 'a', None, True)          :'startwrapusing',
  
      #
  
      ('insert', 'new', None, 'xml', True)  :'startwrapxmlins',
      ('i', 'n', None, 'x', True)           :'startwrapxmlins',
  
      ('new', None, 'xml', True)            :'startwrapxml',
      ('n', None, 'x', True)                :'startwrapxml',
  
      #
                                           
      ('insert', 'new', None, 'text', True) :'startwraptextins',
      ('i', 'n', None, 't', True)           :'startwraptextins',
                                           
      ('new', None, 'text', True)           :'startwraptext',
      ('n', None, 't', True)                :'startwraptext',
                                       
      #                                
  
      ('insert', 'new', None, 'print', True):'startwrapprintins',
      ('i', 'n', None, 'print', True)       :'startwrapprintins',
  
      ('new', None, 'print', True)          :'startwrapprint',
      ('n', None, 'print', True)            :'startwrapprint',
  
      ('new', None, 'attr', True)           :'startwrapattr',
      ('n', None, '*', True)                :'startwrapattr',
  
      #
  
      ('insert', 'new', None, 'set', None, True):'startwrapsetins', 
      ('i', 'n', None, '+', None, True)         :'startwrapsetins',
                                          
      ('new', None, 'set', None, True)      :'startwrapset', 
      ('n', None, '+', None, True)          :'startwrapset',
                                          
      #                                   
                                          
      ('insert', 'new', True)               :'startwrapins',
      ('i', 'n', True)                      :'startwrapins',
                                          
      ('new', True)                         :'startwrap', 
      ('n', True)                           :'startwrap',
                                          

  ###'new' command variations
  
  ('test', True)                            :'if', 
  ('cond', True)                            :'if', 
  ('?', True)                               :'if',
                                            
  ('elif', True)                            :'elif',
  ('e', True)                               :'elif',
                                            
  ('else', False)                           :'else',  
  ('e.', False)                             :'else',  
                                            
  ('for', None, 'in', True)                 :'loop', 
  ('loop', None, 'in', True)                :'loop', 
                                            
  ('overlay', None, False)                  :'overlay', 
  ('o', None, False)                        :'overlay',
                                             
  ('overlay', None, True)                   :'overlay', 
  ('o', None, True)                         :'overlay',
                                            
  ('pass', False)                           :'pass', 
  
  #the following are implicitly added by the scoping engine, fyi.
  ('endnew', False)                         :'endwrap',
  ('endloop', False)                        :'endloop',
  ('endtest', False)                        :'endif',
}
    
