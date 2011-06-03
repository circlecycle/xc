
# Filename: Parser.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)


#turns transform modules into
#a list of Transforms that can be returned
#and evaluated on tags using Processor.py

import sys, string, xml.sax.saxutils, re, copy, os.path
from xml.dom.minidom import parse, parseString

import Config, Instance, Parser_Setup
import Transform as TransformFactory 
from Utils import dbug_func as dbug
from Utils import ArgvShell, ArgvMacroShell, DefaultTypeDict, GetIndent, JumpToNextMacro, Indexer, RecurString, Logger
import Utils

logger = Logger()

setup = Config.setup

slotsym = re.compile("\$\$\w+")
macrodex = {}
Skins = {}

class TransformsParser:
  #this will hold all errors that are encountered in processing, as a singleton. Thus, it
  #needs to be cleared after each complete load cycle (multiple modules)
  #In the manager, it can then test for any and not assign this module to replace the previous
  #(correct) one. This way you can get all your error messages at once, instead of the bummer
  #run-fix-run-fix buisness.
  collectedErrors = []
  
  varsym = re.compile('\[\=.*?\=\]')
  subslotsym = re.compile('^\s*\w+\:\:')
  slotsym = re.compile('^\s*\w+\:')
  evalsym = re.compile('((\[\~)[^\~]+?(\~\]))')
  justIndex = re.compile('^\s*\d\s*$')
  reprIndex = re.compile('^\s*`\s*\d+\s*`\s*$')
  reprExpr = re.compile('^\s*`\s*.*?\s*`\s*$')
  justName = re.compile('^\s*\w+\s*$')
  
  macroLibrary = {}
  
  def __init__(self, fromString=None, sourceFile=None, basepath=setup.basePath):
    """ Generates the hooksList, containing indexes and attributes to each
      rule in the mxml source so that we can cleanly iterate over them. """
      
    #!macrodex should be unique across modules, so we will use a global across all modules processed!
    global slotsym, macrodex, Skins
      
    #hooksList: build the list of transforms that will ultimately be 
    #iterated over (applied) to the source html
    self.hooksList = []
    self.modulename = sourceFile
    self.lastIndent = []
    self.AllMacrosLoaded = []
    self.skin = {}
    self.macrosLoaded = {}
    self.addStartAndFinishTracker = {}
    initShellNeeded, paramArray, value, lastTransform = False, [], '', ''
    globalGroups = []
    self.touchModules = []
    
    #convience base path to the current file
    filePathWithoutExtension = basepath+sourceFile+'/'+sourceFile
    
    #)Load in the transform module in question
    if fromString:
      #if they passed in a string instead of a file
      self.fp = fromString
    else:
      #if they pass in the name of a file to open, then find the files if they exist and parse them
      
      #)try to open the .xc (macr) file, else use an empty .xc mfile
      if os.path.exists(filePathWithoutExtension+'.xc'):
        self.fp = [string.rstrip(x) for x in open(filePathWithoutExtension+'.xc').readlines()]
      else:
        #make an empty transform to parse
        self.fp = ['', '', '']
        
    #)initialize the state machine to begin parsing.
    state = 'transforms'
    lastIndent = 0
    lastGoodIndent = None
    textbuffer = ""    
    #?emptylinecounter: if a empty (blank line) is encountered, count how many we get consecutively
    #if we are storing, then this is the number of \n to insert. this method
    #allows us to end if the indent backs out, but to recover if we don't leave
    #the scope when we encounter the next text, essentially, we get blank lines allowable
    #in text blocks (yay!)
    emptylinecounter = 0
    i = -1
    #?start the state machine off the right way
    self.fp.insert(0, "")
    #?include it's own macro file (if present!) Cheap way to get the effect
    #?since most cool effects are text processing shortcuts anyway
    self.fp.insert(1, "include %s"%sourceFile)
    #?if no start/finish transform in ANY of the input, then add 
    #?one so we can count on an empty one later.
    self.addTransIfNotFound('start')
    self.addTransIfNotFound('finish')
    #?make sure the state machine ends right too by
    #?sneaking a couple in at the end.. how <sar>devious</casm>. ha.
    self.fp += ['eof', '']
    
    #########################################################################
    # <j.brown>Stay on the scene, like a state machine!</j.brown>
    # Let's overview. The states are (in order of a normal run, 
    # but not including (possibly) the last line of the file or the 
    # one-single-text-block keywords like "doc", we have:
    #   transform -> [rules -> [store] -> commit] -> transform
    # if a secondary transform type is detected the last primary one recieves it.
    # A round of initial upkeep on every state EXCEPT the commit state (super upkeep) 
    # simmer at 350 for 4 days, until the iterations are crisp.
    # 
    #########################################################################
    bomb = 0
    bugg = []
    while i < len(self.fp)-1:
      # Loop Upkeep
        
      #we do NOT upkeep (increment the line number, tab counts, among other things)
      #when we are commiting a block.
      if state != 'commit':
        #upkeep
        i += 1
        #bugg.append(self.fp[i])
        line  = string.rstrip(self.fp[i])
        strippedLine = string.strip(self.fp[i])
        
        #skip lines with these things:
        if len(strippedLine) == 0:
          if state == 'store':
            #but include blank lines in code/text blocks..
            emptylinecounter += 1
          continue
          
        #Comments get filtered out UNLESS they are tabbed farther into scope so as
        #to allow comments in text blocks.
        if strippedLine.startswith('#'):
          if state != 'store': 
            continue
          else:
            tmpdent = GetIndent(line)
            if tmpdent <= lastGoodIndent:
              continue
        
        #calculate a tab indent value:
        theIndentMovedOut, theIndentMovedIn = False, False
        theNewIndent = GetIndent(line)
          
        if lastGoodIndent > theNewIndent:  
          theIndentMovedOut = True
          emptylinecounter = 0
          
        #..if it's a shell wrapper transform, then, place the shell command at char indent 1 (one), there by utilizing
        #the 'hidden' indent to provide scope without moving the scope of the block in
        if initShellNeeded and state == 'rules' and self.hooksList and self.hooksList[-1].kind == 'shell': 
          initShellNeeded = False
          self.fp.insert(i," %s"% self.hooksList[-1].shell)
          #raise `self.fp[i]`
          i -= 1
          continue
          
        #If the indent is zero look for the start of a transform
        if (theNewIndent == 0 and state == 'rules'):     
          #?end of transform - time for some cleanup. What cleanup? 
          #well for now just remove the 'module.process' name of the transform from the tag, automatic, like.
          #also 'flush' the Scopey for implicit closure of tags by setting it's indent (position) to zero. That
          #will cause all unset scoping closes to fire off and be recognized.
          #commit to the right place for the secondary transform type requested
          if lastTransform == 'rules':
            transform = self.hooksList[-1]
          elif lastTransform in Parser_Setup.secondaryTransforms:
            if lastTransform == 'error':   
              transform = getattr(self.hooksList[-1], lastTransform+'Handler')[-1]
            else:                 
              transform = getattr(self.hooksList[-1], lastTransform+'Handler')
          else:
            transform = self.hooksList[-1]
            
          for rulesCollected in self.scoper.withdraw(theNewIndent):
            newclose, newsnap = rulesCollected
            if type(newsnap) != type(False):
              transform.rules[newsnap].append(len(transform.rules))
            if type(newclose) != type(False):
              transform.new(newclose, [], '')
              
          if self.hooksList and (lastTransform not in Parser_Setup.transformsWithoutAttrToRemove+Parser_Setup.textSecondaryTransforms):
            if lastTransform in Parser_Setup.secondaryTransforms:
              if lastTransform == 'error':
                getattr(self.hooksList[-1], lastTransform+'Handler')[-1].new('remove', [], self.hooksList[-1].attrname )
              else:
                getattr(self.hooksList[-1], lastTransform+'Handler').new('remove', [], self.hooksList[-1].attrname )
            else:
              self.hooksList[-1].new('remove', [], self.hooksList[-1].attrname )
            pass #dbug("\tADDED the normal (end-of-transform auto) remove: " + self.hooksList[-1].attrname)
          state = 'transforms'
          pass #dbug("\nLooking for a transform again, at State: "+state+"Line: "+line + " Buffer: " + textbuffer)
          i -= 1
          
          pass #dbug('\n'.join([`x`+': '+`y` for x, y in enumerate(self.hooksList[-1].rules)]))
          continue
          
      #?     Generic Rules Handler 1.0
      
      #this matches an entry from the dictionary in Parser_Setup to a line
      #in the XC source being parsed. as such, it's extendable; this code
      #need not be changed.
      
      #two states so far are transforms and rules, transforms are mostly different because
      #they are always on one line and have n extra arguments
      trace = False
      if state == 'rules':    commandSet = Parser_Setup.ruleConfig
      elif state == 'transforms': commandSet = Parser_Setup.transformConfig
      else:           commandSet = None
      if commandSet:
        #determine which command fits the line using ruleConfig
        sorter = [(len(x),x) for x in commandSet.keys()]
        sorter.sort()
        sorter.reverse()
        searchtuple = [x[1] for x in sorter]
        matches = []
        command = strippedLine.split()
        for tokens in searchtuple:
          found = True
          #if the token is longer then the command (by virtue of extra fields, it's not the one we want.)
          if len(tokens)-1 > len(command): found = False
          for j in range(min(len(tokens)-1, len(command))):
            if not tokens[j]:     
              continue
            if tokens[j].lower() != command[j].lower(): 
              found = False
            if len(tokens[j]) > len(command[j]):
              found = False
          if found:
            if not tokens[-1] and (state != 'transforms'):
              if len(command) != len(tokens)-1: continue
            matches.append(list(tokens))
            continue
        #if we find mutliple matches, cull them. Policy below is to 
        #take the longest match available unless the command is exactly
        #the length of one of the matches.
        if matches != []:
          biggest = []
          for x in matches: 
            if len(x)-1 == len(command): 
              biggest = x
            elif len(x)>len(biggest): 
              biggest = x
          keydex, matchingToken = tuple(biggest), biggest
        else:
          #?Macros
          #if it's not found then check loaded macros for a possible expansion
          #set self.fp[i] to macro'd version and decrement i
          if state == 'rules':                    
            name = command[0][:]
            params = command[1:]
            #for reuse in setting defaults, this block of code has been abstracted to extractMacroArguments(). 
            #It links tighly to the class so it only needs the current index, name, and parameter string of line..
            #it will always look to self.fp[] for content. returns the type of macro detected and the scope 
            #at which the the macro was performed.
            mod = 'Unspecified'
            try:
              if not name.count('.'):   mod = self.modulename
              else:                     mod, name = name.split('.')
            except:
              raise "Problem with macro: mod: %s, name:%s"%(mod, name)

            if not self.macroLibrary.has_key(mod):
              raise "Macro not found: file: %s, line %s, Named %s.%s"%(sourceFile, i, mod, name)
                
            if self.macroLibrary[mod].has_key(name):
              macro = self.macroLibrary[mod][name]
              typeis, targetdepth, macro = self.extractMacroArguments(i, theNewIndent, macro, params)
              #raise '\n'.join(["%s: %s"%(x, self.currentMacros[x]) for x in self.currentMacros.keys()])
              if typeis != 'expand':
                index = int(i)
                #?APPLY MACRO OR SHELL.. (EXPANSION DONE above already in self.extractMacroArguments() - weird but true; some selfiness here) 
                treatedlines = self.processFunctionArgs(macro=Utils.DictToSpaceWrapper(macro))   
                #raise '\n'.join(self.fp) + '\n'+ `macro`
                for j, line in enumerate(treatedlines):
                  self.fp.insert(index+j, "%s%s"%(' '*(targetdepth), line))
                
                if typeis == "macro":
                  #! TAKE AND REPOSITION 'INNER' CONTENT TO MATCH NEW INDENTATION LEVEL (IF PRESENT)
                  lastline, nextline = index+j, index+j+1
                  if nextline >= len(self.fp): nextline = len(self.fp)-1
                  newdepth, adjdepth = GetIndent(self.fp[lastline]), GetIndent(self.fp[nextline])
            
                  #?if there are lines to reposition at a new scope to match newly inserted rules
                  #?then look for and match the last indentation found. if the last rule is pass, 
                  #?then assume the rule was just there to move the indentation in and erase it
                  #setraise = False
                  if self.fp[lastline].strip() == 'pass':
                    #go back one line when detecting insertion too
                    nextline -= 1
                    del self.fp[lastline]
      
                  #see how much to move
                  for extent, line in enumerate(self.fp[nextline:]):
                    currdent = GetIndent(line)
                    if currdent <= theNewIndent: break
          
                  #and move it.
                  for k in range(extent):
                    currdent = GetIndent(self.fp[nextline+k])
                    self.fp[nextline+k] = "%s%s"%(((currdent-adjdepth)+newdepth)*" ", self.fp[nextline+k].strip())
                    
                  #if setraise: raise `self.fp[lastline]` + '\n'.join(self.fp)
              
              #skip back one line and do it till its done
              i -= 1
              continue

          #raise '<br/>'.join(self.fp)   di
          if self.hooksList[-1]:
            errorInLoading = "Command not matched, in module '%s', transform '%s', line %s: <b>%s</b>" %(sourceFile, self.hooksList[-1].name, str(i+1),' '.join(command))
          else:
            errorInLoading = "Problem with transform name at the top of %s"%sourceFile
          raise `errorInLoading` + '\n' +basepath+ '\n'.join(self.fp)
          self.collectedErrors.append(errorInLoading)
          #this will make it suck the command in anyway - as text - so that the error checking process can continue!
          #i want to give all the errors in all modules at once.
          commandSet = Parser_Setup.ruleConfig
          keydex, matchingToken = [('text', True), ['text', True]]
          command = ['text']
          state = 'store'
        
        if self.hooksList and len(self.hooksList[-1].rules) > 3:
          pass #dbug('Command/Transform/Part is '+`command`+' Last 3: '+`self.hooksList[-1].rules[-3:]`)
        else:
          pass #dbug('Command/Transform/Part is '+`command`)
        

        #extract data from the command to pass to the commit state
        kind = commandSet[keydex]
        if matchingToken.count(None) or state == 'transforms':
          #if the state is transforms, have the resulting match array include all remaining
          #text on the line, if any, as a single string in the paramArray.
          if state == 'transforms':
            padlen = len(command) - (len(matchingToken))
            if padlen > 0: [matchingToken.append(None) for x in range(padlen)]
          try: paramArray = [command[x] for x in range(len(matchingToken)-1) if matchingToken[x] == None]
          except: raise Exception, "%s, %s, %s" % (x, command, matchingToken)
        else:
          paramArray = []
        
        #rules are further subprocessed in the parser while transforms are declared once,
        #state set, and left aside until all the rules are finished.
        if state == 'rules':
          ######################################################################
          # All the scoping action happens in this next block!
          ######################################################################
          
          #commit to the right place for the transform type requested
          if lastTransform == 'rules':
            transform = self.hooksList[-1]
          elif lastTransform in Parser_Setup.secondaryTransforms:
            if lastTransform == 'error':   
              transform = getattr(self.hooksList[-1], lastTransform+'Handler')[-1]
            else:                 
              transform = getattr(self.hooksList[-1], lastTransform+'Handler')
          else:
            transform = self.hooksList[-1]
          #Code scoping mechanism lives here, since it's run on each rule parsed. It determines
          #whether extra close rules should be added in accordance with the indentation-level detected.
          #it also inserts additional open/close pairs if a rule calls for that.
          #The Scopey class at the bottom of the page does the book-keeping.

          for rulesCollected in self.scoper.withdraw(theNewIndent, nextkind=kind):
            newclose, newsnap = rulesCollected
            if type(newsnap) != type(False):
              transform.rules[newsnap].append(len(transform.rules))
            if type(newclose) != type(False):
              transform.new(newclose, [], '')

          #more of it... this is the part that reports new open scopes
          if kind in Parser_Setup.rulesWithScope.keys():
            #uhoh.. one special case! 'multi' is how many (identical!) closes a rule needs, which Scopey supports doing.
            if kind == 'startwrap' or kind == 'startwrapins':
              #we need the tag types to open for the rule which would otherwise be processed later.. we need it now to make
              #the multiple opens (since most commands are one rule per 'command', this is a special case). since we know 
              #the rule *is* startwrap (and hence it's form), we can get it here. Special case messy, but i like the compaction 
              #it gives the code
              sw_text = string.join(command[len(matchingToken)-1:], ' ')
              opens = [x.strip() for x in sw_text.split(',')]
              multi = len(opens)
              #add the needed number of opens required, log the closes needed
              #and (tested for right below, take a look) skip doing any other rule adding.
              for entry in opens:
                transform.new('startwrap', [], entry)
              self.scoper.advance(theNewIndent, rule=Parser_Setup.rulesWithScope[kind], multi=multi)
            #another 'hack' if a command issues two different nested rules (like both loop and startwrap) the we have a LITTLE
            #leeway - see, if indentation can't be less the two chars, then we know the progression of the scoping array will always be guaranteed
            #to have at least one extra spot availble. use it to make the two-rule pair. We don't get snazzier then this, however, and i can't
            #(right now)
            elif kind in ['loopusing', 'loop']:
              self.scoper.advance(theNewIndent, rule=Parser_Setup.rulesWithScope[kind], snapback=len(transform.rules))
              if kind == 'loopusing':
                self.scoper.advance(theNewIndent+1, rule=Parser_Setup.rulesWithScope['startwrap'])
              pass #dbug('lu scoped: '+`kind`+' / '+command[3]+' indent: '+`theNewIndent`)
            #another 'hack' for the if statements - these need to record where a rule closes ahead of time, that is
            #when a rule of these types closes, the opening rule has it's close-rule-location recorded. This facilitates
            #jumping to the next block if a test is false or a match has already been found.
            elif kind in Parser_Setup.rulesWithSnapback:
              self.scoper.advance(theNewIndent, rule=Parser_Setup.rulesWithScope[kind], snapback=len(transform.rules))
            else:
              self.scoper.advance(theNewIndent, rule=Parser_Setup.rulesWithScope[kind])
              
              
          #we took care of adding the start commands made above, IF it's a startwrap command (special case)
          if kind == 'startwrap' or kind == 'startwrapins':
            state = 'rules'
            textbuffer = ""
            continue
            
          ######## That's it for scoping, except for a bit possibly before a rule is committed much below #################### # # #  #   #    #
          
          if matchingToken[-1] == False:
            state = 'commit'
            continue
          #if there are additonal args on the same line
          if len(command) > len(matchingToken)-1: 
            state = 'commit'
            textbuffer = string.join(command[len(matchingToken)-1:], ' ')
            continue
          #if they are using multiline.
          else:
            state = 'store'
            continue  
        
      ######################################################################
      #     Handle the start of a block (make new transform)
      ######################################################################
      
      if state == 'transforms': 
        #keep this around for the commit stage.
        lastTransform = kind
        
        #they request an informal end of file, the transform authors can store
        #code snippets or something beneath this if they like.
        #it also supports the parser ending normally. two birds :)
        if kind == 'EOF':
          break
          
        #the primaryTransforms are 'first-rate'; able to be called by the programmer.
        #this is where we are initializing a new transform, then.
        if kind in Parser_Setup.primaryTransforms:
          
          #if a global group (or series of groups is specified)
          if kind == 'group':       
            args = ' '.join(strippedLine.split(' ')[len(keydex)-1:])
            globalGroups += [x.strip() for x in args.split(',')]
            continue
          
          #if they want to include a macro file on this run, load it in and continue.
          #cool things: if the macro file defines a start transform, a line to invoke it 
          #is added to it to facilitate automatic initialization on include.
          if kind == 'include':
            args = ' '.join(strippedLine.split(' ')[len(keydex)-1:])
            self.loadMacrosToList("%s, %s"%(self.modulename, args), trace=[sourceFile], into=self.modulename)
            #if after that a start macro was made, add that to the start transform in the transform (or make a new one if it's not') _textually_
            if self.macroLibrary.has_key(self.modulename):
              specialTransTypes = ['start', 'finish']
              for specialType in specialTransTypes:
                typekey = "%s%s"%(self.modulename, specialType)
                if self.macroLibrary[self.modulename].has_key('%s_'%specialType) and not self.addStartAndFinishTracker.has_key("%s%s"%(self.modulename, specialType)):
                  self.addStartAndFinishTracker[typekey] = True
                  specialName = "%s.%s_"%(self.modulename, specialType)
                  for j, entry in enumerate(self.fp):
                    if entry.strip() == specialType:
                      dent = GetIndent(self.fp[j+1])
                      self.fp.insert(j+1, '%s%s'%(' '*dent, specialName))
                      break
            continue
            
          if kind == 'skin':
            arg = ' '.join(strippedLine.split(' ')[len(keydex)-1:])
            skinpath = "%s%s/%s.xcs"%(basepath, sourceFile, arg)
            #)Try to open the skin file if it exists and parse it in, else use an empty skin.
            if os.path.exists(skinpath):
              if not Skins.has_key(sourceFile): Skins[sourceFile] = {}
              newskins = self.processSkin(skinpath)
              for entry in newskins.keys():
                Skins[sourceFile][entry] = newskins[entry]
            else:
              raise "In %s, the requested skin file at %s does not exist."%(sourceFile, skinpath)
            continue
          
          #make a new scoper
          self.scoper = Scopey()
          #Most transforms are of the form 'tag.name', but a few forms have "defaults" -- that is,
          #they only have one name. If that's the case, perform the correct actions to flesh those types out.
          if paramArray:
            tagAndTrigger = string.split(paramArray[0], '.')
            if len(tagAndTrigger) == 1: 
              if kind == 'filter':  kind = 'filterall'
              elif kind == 'server':  kind = 'serverfragment'
              elif 'laszlo' in kind.lower(): tagAndTrigger = ['object', tagAndTrigger[0]]
              else:         raise Exception, 'error in %s at line %s: transform type should have name X.Y for tagtype and transform name, respectively.'%(sourceFile, i)
          else:
            tagAndTrigger = paramArray
            
          if kind == 'filterall':     paramArray = [tagAndTrigger[0], '']
          #in this case, textonly means return a 'fragment' transform - no outer node, but a series of interior ones.
          #this terminology makes sense when considering transforms other then servers that only return text with no outer node,
          #but both rely on the same mechanism that responds to 'fragment' tag types.
          elif kind == 'serverfragment': paramArray = ['fragment', tagAndTrigger[0]]
          elif kind == 'stateful':    paramArray = ['', '_STATEFUL'] 
          elif kind == 'stateless':   paramArray = ['', '_STATELESS'] 
          elif kind == 'reqstart':    paramArray = ['', '_STARTREQ'] 
          elif kind == 'reqend':      paramArray = ['', '_ENDREQ']
          elif kind.startswith('filter'): paramArray = [tagAndTrigger[0], tagAndTrigger[1]]
          elif kind.startswith('server'): paramArray = [tagAndTrigger[0], tagAndTrigger[1]]
          elif kind.startswith('define'): paramArray = [tagAndTrigger[0], tagAndTrigger[1]]
          elif kind.startswith('inherit'):paramArray = [tagAndTrigger[0], tagAndTrigger[1], paramArray[1]]
          elif kind.startswith('preherit'):paramArray = [tagAndTrigger[0], tagAndTrigger[1], paramArray[1]]
          elif kind.startswith('laszlo'): paramArray = [tagAndTrigger[0], tagAndTrigger[1]]  
          elif kind.startswith('shell'): 
            initShellNeeded = True
            paramArray = [tagAndTrigger[0], tagAndTrigger[1], paramArray[1]]  
            
          #in the restricted transforms, dump the remainder of the line as an argument to the factory.
          #this uses the keydex (key index) from the command parser above, which is the matching tuple we found --
          #this reveals how long the command is, thus, where i can cleave the line to get that info.
          if kind in Parser_Setup.restrictedTransforms:
            #permissible becomes a ['x','x','x'] from a 'x,x,x'
            permissible = [x.strip() for x in string.split(' '.join(string.split(strippedLine, ' ')[len(keydex)-1:]), ',')]
            paramArray.append(permissible)
            
          #parser grabed different params then filter, define, etc type and makes transforms
          NewTransform = TransformFactory.Transform(kind, self.modulename, paramArray)
          
          if globalGroups != []:
            if NewTransform.authorized == False: NewTransform.authorized = []
            [NewTransform.authorized.append(x) for x in globalGroups if x not in NewTransform.authorized]
          
          #an alias has nothing done it it, except to have a single pass inside it. set that up
          if kind == 'inheritAlias':             
            state = 'transforms'
          else:
            state = 'rules'
          
          #is it a server page, requiring the input of modules to import on it?
          if kind == 'serverPage':
            #neat little line to get what ever is after the command literally, almost like a normal rule..
            #The toImport attribute will be read later by the server to decide if it should construct an html shell instead
            #of a single root node tag.
            NewTransform.toImport = "%s,%s"%(self.modulename, ' '.join(string.split(strippedLine, ' ')[len(keydex)-1:]).strip())
          self.hooksList.append(NewTransform) 
          continue
          
        #if the transform type is rules, just start getting rules.
        elif kind == 'rules':
          #get a fresh indented/state tracker
          self.scoper = Scopey()
          state = 'rules'
          continue
  
        #prepare the parser to suck in a secondary transform (that is, a transform block appended to
        #a list of like purposed transforms to achieve some conditional rendering abilities, like
        #denied and error rendering branches.)
        elif kind in Parser_Setup.secondaryTransforms and kind not in Parser_Setup.textSecondaryTransforms:
          #get a fresh indented/state tracker
          tagAndAttrToHook = [self.hooksList[-1].tag, self.hooksList[-1].atomicname] 
          NewTransform = TransformFactory.Transform(kind, self.modulename, tagAndAttrToHook)
          if kind == 'error':
            getattr(self.hooksList[-1], kind+'Handler').append(NewTransform)
          else:
            setattr(self.hooksList[-1], kind+'Handler', NewTransform) 
          state = 'rules'
          continue
      
        #prepare the parser to suck in a pure text secondary transform
        elif kind in Parser_Setup.textSecondaryTransforms:
          tagAndAttrToHook = [self.hooksList[-1].tag, self.hooksList[-1].atomicname] 
          NewTransform = TransformFactory.Transform(kind, self.modulename, tagAndAttrToHook)  
          setattr(self.hooksList[-1], kind+'Handler', NewTransform)
          state = 'store'
          kind = 'text'
          theLastIndent = None
          continue
      
        raise Exception, "Possible Syntax Error parsing "+`sourceFile`+" containing: "+`line`
      
      ######################################################################
      #   Store a text block state (we are in Rules if we are here)
      ######################################################################
      
      if state == 'store':
        if not lastGoodIndent:
          lastGoodIndent = theNewIndent
          
        if theIndentMovedOut==True:
          state = 'commit'    #state_data has already been set by another function
          lastGoodIndent = None 
          i -= 1          #don't move forward - this line told us to commit
          continue

        if emptylinecounter:
          textbuffer += '\n'*emptylinecounter
          emptylinecounter = 0
          
        #preserve origninal indenting if in the fullTextRules group
        if sum([x in kind for x in Parser_Setup.fullTextRules]):  
          textbuffer += line[lastGoodIndent:] + "\n"
          pass #dbug("\t\tstoring: " + line[lastGoodIndent:] )
        #default. whitespace is trimmed to a single space
        else:                  
          textbuffer += strippedLine
          pass #dbug("\t\tstoring:" + strippedLine )
        continue
        
      ######################################################################
      #     Commit a closed rule to the object
      ######################################################################
      
      if state == 'commit':
        #set next state, this MAY be overrided from the commitCommand!
        state = 'rules'
        #commit to the right place for the secondary transform type requested
        if lastTransform == 'rules':
          transform = self.hooksList[-1]
        elif lastTransform in Parser_Setup.secondaryTransforms:
          if lastTransform == 'error':   
            transform = getattr(self.hooksList[-1], lastTransform+'Handler')[-1]
          else:                 
            transform = getattr(self.hooksList[-1], lastTransform+'Handler')
        else:
          transform = NewTransform
          
          
        if kind in Parser_Setup.checkxml:
          #VERY IMPORTANT LOGICAL BIT: we substitiute all vars ([~...~]) with the
          #word 'test' and THEN check for correctness. This is because
          #there are situatitions where you want to use such syntax in forming
          #tags themselves! That isn't legal xml tho, so we fake it, qed.
          try:
            origText, finalText, processList = textbuffer, textbuffer, []
            #okay - each time it finds a match record it's location (and extract interior to)
            #a processing list to consider in the next block. no match means it 'll skip the next loop.
            #i just got down with regexs again, so i think i'll be updating this soon.
            while 1:
              match = Instance.matchTextVar.search(textbuffer)
              if not match: break
              x, y = match.span()
              fulltag = textbuffer[x:y]
              attrToReplace = textbuffer[x+2:y-2]
              toreplace = [fulltag, attrToReplace]
              if toreplace not in processList:
                processList.append(toreplace)
              textbuffer = textbuffer[y:]
              
            #else begin replacment of variables
            for entry in processList: 
              finalText = string.replace(finalText, entry[0], 'test')
            a = parseString("<null>"+finalText+"</null>")
            textbuffer = origText
          except Exception, msg: 
            self.collectedErrors.append("Bad XML in "+self.hooksList[-1].name+" rule: "+kind+" msg: "+str(msg))
            textbuffer = ""
            continue
            
        if kind in Parser_Setup.checkpython or lastTransform == 'init':
          #'couse when we check the code by compiling it, might as well save it in the transform to use.
          try: compile(textbuffer, "<string>", "exec")
          except Exception, msg: 
            self.collectedErrors.append("Bad Python Syntax in "+self.hooksList[-1].name+" rule: "+kind+" msg: "+str(msg))
            textbuffer = ""
            continue
          
        if [True for x in Parser_Setup.escapedRules if kind in x]:
          #Properly escape the text if it's an escaped rule
          transform.new( kind, paramArray, xml.sax.saxutils.escape(textbuffer) )
        else:
          #just remove the last linebreak (unneeded?) - if it's excutable python or something..
          if type("") is type(textbuffer):
            if textbuffer:
              if textbuffer[-1] == '\n':
                textbuffer = textbuffer[:-1]
            
          transform.new( kind, paramArray, textbuffer )
          
          #if kind is loopusing, we need to put a new startwrap rule AFTER the new loop rule,
          #so that the opening matches the closing. That's why we have to do it here and not above with
          #the other scoping code above!
          if kind == 'loopusing':
            transform.new('startwrap', [], command[1])
            
        pass #dbug("\tRULE: "+str(kind)+": ")
        textbuffer = "" #reset the buffer
        continue

      #end of loop upkeep on indenting.
      theLastIndent = theNewIndent
      lastIndent = theNewIndent
      
    #? HERE do operations that relate to the entire module.. (if any)
    
    #if self.modulename == 'tester': raise '<br/>'.join([x for x in bugg])
    #if self.modulename == 'tester': 
    #  rules = '<br/>'.join([`x` for x in transform.rules])
    #  fppretty = '<br/>'.join(self.fp)
    #  raise rules + fppretty
    
  def listOfAllTransforms(self):
    return self.hooksList
   
  #) Complete solution for loading the macro languages grammar to dictionary. simple but stateful (confusing)
  def loadMacrosToList(self, arg, trace=[], into=False):
    global Skins
    filesthisrun = [x.strip() for x in arg.split(',') if x]
    for atomicname in filesthisrun:      
      
      #?save this, it's handy for storing
      realatomicname = False
      filePathWithoutExtension = "%s%s/%s"%(setup.basePath, atomicname, atomicname)
        
      #?if we have already loaded this module into a target (or false -- itself) then DON'T do it again.
      macroKey = "%s%s"%(into,atomicname)
      if self.macrosLoaded.has_key(macroKey):
        continue
      self.macrosLoaded[macroKey] = True
      
      #?save the fact that we have loaded this macro file    
      self.AllMacrosLoaded.append(atomicname)
        
      #?'if not into' means that we aren't being told to specifically put macro into another macro modules
      #?space..
      if into: 
        realatomicname = atomicname
        atomicname = into
        #?skip loading macro files twice (TBD)
        #if self.macroLibrary.has_key(realatomicname):
        #  for entry in self.macroLibrary[realatomicname].keys():
        #    self.macroLibrary[into][entry] = self.macroLibrary[realatomicname][entry]
        #  continue
        
      #?initializse where we store the macros for this run if not already..
      if not self.macroLibrary.has_key(atomicname):
        self.macroLibrary[atomicname] = {}
      if realatomicname: 
        if not self.macroLibrary.has_key(realatomicname):
          self.macroLibrary[realatomicname] = {}
      
      try:    toload = open("%s.xcm"%(filePathWithoutExtension)).read().split('\n')
      except: continue  #if they don't have a macro file don't complain, just don't load
        #raise "Can't open the macro file %s%sXC"%(setup.basePath, atomicname)
        
      committingBlock = False
      i = -1
      while i < len(toload)-1:
        i += 1
        entry = toload[i]
        
        #?if EOF encountered, we are done.
        if entry.strip() == 'eof': break
        #?skip blanks and comments
        if not entry.strip() or entry.strip().startswith('#'): continue
          #?if a macro is being loaded in
        if committingBlock:
          #?if still indented they are in the same macro
          if getindent: 
            getindent, indent = False, GetIndent(entry)
          currdent = GetIndent(entry)
          if not currdent:
            #?save the now ended macro
            self.macroLibrary[atomicnameToUse][nameToUse] = {'type_':typeis, 'mod_':realatomicname, 'source_':remainder, 'trace_':trace, 'name_':nameToUse}
            if realatomicnameToUse: self.macroLibrary[realatomicnameToUse][nameToUse] = self.macroLibrary[atomicnameToUse][nameToUse]
            committingBlock = False
            #if nameToUse == 'method': raise `self.macroLibrary[atomicnameToUse][nameToUse]`
          else:
            #?save the strip()'d entry and how deeply indented it was
            remainder.append(ArgvMacroShell(entry[indent:]).using())
            continue
            
        #?have a new macro to examine and load
        name = entry.strip().split(' ')[0][1:]
        params = [x for x in entry.strip().split(' ')[1:] if x != '']
        orig = entry.strip()
        
        #?include other macro files on command
        if orig.startswith('include'):
          trace.append(atomicname) #trace keeps track of just where we got a macro loaded from - since it's a flat namespace for now, that helps.'
          self.loadMacrosToList(' '.join(params), trace=trace, into=atomicname)
          continue
          
        #?have we loaded the skin for this macro file yet? if not do so
        if orig.startswith('skin'):
          skinpath = "%s%s/%s.xcs"%(setup.basePath, realatomicname, params[0])
          #)Try to open the skin file if it exists and parse it in, else use an empty skin.
          if os.path.exists(skinpath):
            if not Skins.has_key(realatomicname): Skins[realatomicname] = {}
            newskins = self.processSkin(skinpath)
            for entry in newskins.keys():
              Skins[realatomicname][entry] = newskins[entry]
          else:
            raise "In %s, the requested skin file at %s does not exist."%(realatomicname, skinpath)
              
        #?include other macro files on command
        elif orig.startswith('import'):
          trace.append(atomicname) #trace keeps track of just where we got a macro loaded from - since it's a flat namespace for now, that helps.'
          self.loadMacrosToList(' '.join(params), trace=trace)
          continue
          
        #?process a 'default' entry and add it to the macro being made, as if it came from the XC source
        elif orig.startswith('='):
          try:
            self.extractMacroArguments(i, 0, self.macroLibrary[atomicname][name], params, bufTarget=toload, default=True)
          except Exception, msg:
            raise Exception, "A default, '%s', is being made before the macro for that default, line %s, file %s.macro, also %s"%(name, i, atomicname, msg)
          #go back one line and continue - extractMacro gobbled the line right up to it, so we don't want to advance.
          i -= 1
          continue
          
        #?if it doesn't start with '@' then it's not a valid macro definition
        elif orig.startswith('@') or orig.startswith('start') or orig.startswith('finish'):          
          nameToUse, atomicnameToUse, realatomicnameToUse = name, atomicname, realatomicname
          #?has params; make a single new entry
          if orig.startswith('start'):
            #?change the target on a start to point to itself even if it's an 'into' load
            atomicnameToUse = realatomicname
            realatomicnameToUse = False
            nameToUse = 'start_'
          elif orig.startswith('finish'):
            #?change the target on a start to point to itself even if it's an 'into' load
            atomicnameToUse = realatomicname
            realatomicnameToUse = False
            nameToUse = 'finish_'
            
          if params:
            justargs = ' '.join(params)
            if not self.varsym.search(justargs):
              self.macroLibrary[atomicnameToUse][nameToUse] = {'type_':"expand", 'mod_':realatomicname, 'source_':ArgvMacroShell(justargs).using(), 'trace_':trace, 'name_':nameToUse}
              if realatomicnameToUse: self.macroLibrary[realatomicnameToUse][nameToUse] = self.macroLibrary[atomicnameToUse][nameToUse]
            else:
              self.macroLibrary[atomicnameToUse][nameToUse] = {'type_':'macro', 'mod_':realatomicname, 'source_':[ArgvMacroShell(justargs).using()], 'trace_':trace, 'name_':nameToUse}
              if realatomicnameToUse: self.macroLibrary[realatomicnameToUse][nameToUse] = self.macroLibrary[atomicnameToUse][nameToUse]
          else:
            #?if there are no parameters then it's multiline. Treat accordingly.
            remainder, typeis, committingBlock, getindent, currdent = [], 'macro', True, True, True
        else:
          raise 'All macro definitions start with @ or =, line %s, file %s: %s.xcm'%(i, entry, atomicname)
      if committingBlock:
        try:
          self.macroLibrary[atomicnameToUse][nameToUse] = {'type_':typeis, 'mod_':realatomicname, 'source_':remainder, 'trace_':trace, 'name_':nameToUse}
          if realatomicnameToUse: self.macroLibrary[realatomicnameToUse][nameToUse] = self.macroLibrary[atomicnameToUse][nameToUse]
        except Exception, msg:
          raise `atomicname` + `nameToUse` + `remainder` + str(msg)
    
    
  #) Extract arguments from the current index of self.fp, using a macro name and a parameter string.       
  def extractMacroArguments(self, index, theNewIndent, macro, params, bufTarget=False, default=False ):
    if not bufTarget: bufTarget = self.fp
    
    #if it's not a default being made, then a copy will be produced that will be macro
    #used for this particular run.
    if not default:
      macro = macro.copy()
      
    checkme = False
      
    name = macro['name_']
    if name:
      typeis = macro['type_']
      trace = macro['trace_']
    else:
      #if it doesn't have a name it's a special type start_ or finish_
      del macro['name_']
      typeis = 'macro'
      
    noneWatch = False   #noneWatch puts a none in the preceding entry if consecutive keyword arguments have no paramters..

    #?EXPANSION
    if typeis == "expand":
      macrosource = macro['source_']
      bufTarget[index] = "%s%s %s"%(' '*(theNewIndent), str(macrosource).strip(), ' '.join(params))
      return ['expand', 0, macro]
    #?MACROS & SHELLS
    else:
      blockdepth, fillblock, firstdepth = None, [], False
      targetdepth = GetIndent(bufTarget[index])
      #?type detection to be passed back done here
      if params: 
        macro['ARGV'] = ArgvMacroShell(' '.join(params)).using()
        del bufTarget[index]
        return ['macro', targetdepth, macro]
      elif name:
        macro['type_'] = 'shell'
      for entry in bufTarget[index+1:]:
        tmp = entry.strip()
        if not tmp or tmp[0] == '#': continue
        firstdepth = GetIndent(entry)
        break
      #?if there are no arguments just use the defaults and blow
      if targetdepth >= firstdepth: 
        del bufTarget[index]
        return ['empty',targetdepth,macro]
      #?remove original shell invoke line, and begin
      del bufTarget[index]
      while index < len(bufTarget):
        entry = str(bufTarget[index])
        strippedentry = entry.strip()
        currdepth = GetIndent(entry)
        
        #?skip blanklines and comments since this loop is "outside" of the parser loop that would otherwise do that..
        if (not strippedentry) or (strippedentry.startswith('#') and currdepth <= firstdepth):
          del bufTarget[index]
          continue
        
        #if checkme and not default: raise `bufTarget` + '\n' + `macro`
        if currdepth == firstdepth:
          if noneWatch: 
            if not macro.has_key(noneWatch):
              macro[noneWatch] = ArgvMacroShell('true').using()
            noneWatch = False
          if fillblock:
            macro[storeto] = fillblock
            blockdepth = None
            fillblock = []
          #handle the '::' subslot operator
          if self.subslotsym.search(strippedentry):
            storeto = strippedentry.split('::')[0]
            macro[storeto] = {'name_':None}
            #store the new subslot entry as returned back into macro[storeto]!
            dummy, dummy, macro[storeto] = self.extractMacroArguments(index, blockdepth, macro[storeto], [], default=default)
            #continue to pick up further entries; the above call has deleted the appropiate lines, we're ready to go again
            continue
          else:
            #see, here we'll get the first slot OR find out it's really a parameterless macro.. 
            #!(OR END OF A SHELL SO INDENT REST?!?!?!?!?!)
            if not self.slotsym.search(strippedentry):
              #don't delete next line cause it ain't part of the now discovered macro call..
              if not macro.has_key('ARGV'): 
                macro['ARGV'] = ArgvMacroShell('true').using()
              macro['type_'] = 'macro'
              return ['macro', targetdepth, macro]
            keywordargs = strippedentry.split(':')
            storeto = keywordargs[0]       
            newargs = ':'.join(keywordargs[1:]).strip()              
            if newargs: macro[storeto] = ArgvMacroShell(newargs).using()
            else: noneWatch = storeto
        elif currdepth < firstdepth:
          if noneWatch: 
            if not macro.has_key(noneWatch):
              macro[noneWatch] = ArgvMacroShell('true').using()
            noneWatch = False
          if fillblock: macro[storeto] = fillblock
          break
        elif currdepth > firstdepth:
          if blockdepth == None:  
            blockdepth = GetIndent(entry)
          fillblock.append(ArgvMacroShell(entry[blockdepth:]).using())
        del bufTarget[index]
    
    #catch that last line if it hasn't been committed.
    if noneWatch: macro[noneWatch] = ArgvMacroShell('true').using()
    if fillblock: macro[storeto] = fillblock 
    return ['shell', targetdepth, macro]
    
    
  #) MACRO STUFF
  #! THIS HANDLES TEXT REPLACEMENT FOR THE MACRO USING PARAMETERS FROM THE SOURCE AND 
  #! RULES FROM THE MACRO... just like the one in the Processor, pretty much
  def processFunctionArgs(self, macro):
    global Skins
    if not macrodex.has_key(macro.name_):
      macrodex[macro.name_] = -1
    macrodex[macro.name_] += 1
    i = 0
    count = []
    buf = list(macro.source_)
    entry = False
    while i < len(buf):
      entry = str(buf[i])
      processList = []
    
      #)Slurp in each possible variable replacement, for linear evaluation below
      textEaten = str(entry)
      while 1:
        match = self.varsym.search(textEaten)
        if not match: break
        x, y = match.span()
        fullvartext = textEaten[x:y]
        attrToReplace = textEaten[x+2:y-2]
        toreplace = [fullvartext, attrToReplace]
        if toreplace not in processList:
          processList.append(toreplace)
        textEaten = textEaten[y:]

      #) no matches
      if not processList:
        i += 1
        continue  
        
      fullvartext, attrToReplace = processList[0]  
      #) Full multiline rule replacement?
      if entry.strip() == fullvartext and not attrToReplace.startswith('!'):  
        #this is a flag to coordinate optional inclusion of lines (the [=?xx=] operator)
        removeOnAbsent = False
        currdent = GetIndent(entry)
        del buf[i] #:get rid of variable text itself
        if attrToReplace.startswith('?'): 
          attrToReplace, numCharsCounted = Utils.countAndRemoveBeginningChars(attrToReplace, '?')
          removeOnAbsent = True
        try:
          toloop = macro[attrToReplace]
        except Exception, msg:
          #if we're just supposed to ignore an empty slot, continue
          if removeOnAbsent:  
            #this cute bit of code will remove the lines above the statement, one per question mark used.
            #differs from the singleline removal (below a bit) because the lines already been removed (above)
            #hence the -1 on the range() statement
            indexToRemoveAt = i - (numCharsCounted - 1)
            for removal in range(numCharsCounted-1):
              del buf[indexToRemoveAt]
            continue
          raise "when calling the macro '%s' in '%s', the expression [=%s=] doesn't work because %s"%(macro.name_, macro.trace_, attrToReplace, str(msg)) 
        #?if there is no append attribute it's not a list, it is a string representing a single line slot.
        #?wrap it in a list to loop correctly.
        if not getattr(toloop, 'append', False):
          toloop = [toloop]
        #?insert the rules as stored
        for line in toloop:
          buf.insert(i, "%s%s"%(" "*(currdent), str(line)))
          i += 1
        continue
      
      #)if a normal replacement process (all on one line!)
      removeOnAbsent = False #this is a flag to coordinate optional inclusion of lines (the [=?xx=] operator)
      for vartext in processList: 
        fullvartext, attrToReplace = vartext
        
        #? does this line call in a skin parameter?
        if attrToReplace.startswith('$'):
          removeAbsent = False
          try:
            entry = entry.replace(fullvartext, Skins[macro.mod_][str(attrToReplace[1:])])
          except Exception, msg:
            raise "In the macro %s, module %s, the skin variable %s doesn't exist."%(macro.name_, macro.mod_, str(attrToReplace[1:]))
          continue
        
        try:
          #?if it's a special number only argument, provide the requested macro argument (one line only, comma delim'd by ArgvMacroShell)'
          if self.reprIndex.search(attrToReplace):
            if self.evalsym.search(str(toreplace)):
              raise "when calling the macro '%s', the expression [=%s=] has a blooms variable replacement in a repr() call, which is usually not evaluated for variables.: %s. also, %s"%(macro.name_, attrToReplace, str(msg))
            entry = RecurString(entry.replace(fullvartext, `macro.ARGV[int(attrToReplace[1:-1])]`), typeis='repr')
          elif self.justIndex.search(attrToReplace):
            entry = RecurString(entry.replace(fullvartext, str(macro.ARGV[int(attrToReplace)])))
          #?macro autospacing method is the same as the 'full' version..
          elif attrToReplace.startswith('.'):
            if attrToReplace.startswith('..'):
              attrToReplace = attrToReplace[2:]
              #another mods namespace? or not?
              if '.' in attrToReplace:  mod, attrToReplace = attrToReplace.split('.')
              else:                     mod = macro.mod_
              #if no attr the just yield the modulename, no trailing '_'
              if attrToReplace: entry = entry.replace(fullvartext, "%s_%s"%(mod, attrToReplace)) 
              else:             entry = entry.replace(fullvartext, "%s"%(mod)) 
            else:
              attrToReplace = attrToReplace[1:]
              entry = entry.replace(fullvartext, "%s_%s_%s"%(macro.name_, macrodex[macro.name_], attrToReplace)) 
          else:
            #?if it starts with '?' then set a flag and erase the character - means delete the line it shows up on if the slot doesn't exist (simple optional inclusion!)
            if attrToReplace.startswith('?'): 
              attrToReplace, numCharsCounted = Utils.countAndRemoveBeginningChars(attrToReplace, '?')
              removeOnAbsent = True
            try:
              #?Default: retrieve then eval() a value from the space associated with the transform.
              if self.reprExpr.search(attrToReplace):
                value = eval(attrToReplace[1:-1], macro.__dict__)
                #? if an expression is wrapped in `x` and has a XC var in it, warn them.
                if self.evalsym.search(str(value)):
                  raise "when calling the macro '%s', the expression [=%s=] has a XC variable replacement in a repr() call, which is usually not evaluated for variables.: %s."%(macro.name_, attrToReplace, macro.keys())
                #?Sneaky: rule entries are lists but repr (`x`) makes a string and we lose the ability
                #?to print the "normal" list (because repr of the ArgvMacroShell is called..). By checking 
                #?for a top-level list, we can treat it to look like flat list entries again.
                if getattr(value, 'append', False):
                  value = [str(x) for x in value]
                  if not value[0]: value = []
                elif getattr(value, 'array', False):
                  #if it's a ArgvMacroShell and empty, set to [] because AMS() will be ['']
                  if not value.array[0]: value = ''
                value = `RecurString(value, typeis='repr')`
              else:
                #?just run the expression. if justName - read the macro directly (skips finding builtins like id!)
                #?otherwise full possible python expression, and act on exception or false evaluating entries for line removal
                if self.justName.search(attrToReplace): 
                  value = macro[attrToReplace.strip()]
                else:              
                  value = eval(attrToReplace, macro.__dict__)
                  if removeOnAbsent and not value: 
                    removeOnAbsent = 'used' #flag the engine to delete the line 
                    raise
                  
              #commit list..
              entry = entry.replace(fullvartext, str(value))
            except:
              if removeOnAbsent:
                removeOnAbsent = "used"
                break #this line is finished (and eliminated below), go to the next
              else: 
                raise #or do the normal thing..
        except Exception, msg:
          raise "when calling the macro '%s' in '%s', the expression [=%s=] doesn't work because %s"%(macro.name_, macro.trace_, attrToReplace, str(msg))  
     
      #?set the line and continue unless remove on absent has been performed, above, then just delete the whole line.
      if removeOnAbsent != 'used':
        #do the normal deal
        buf[i] = entry
        i += 1
      else:
        #this cute bit of code will remove the lines above the statement, one per question mark used.
        indexToRemoveAt = i - (numCharsCounted - 1)
        for removal in range(numCharsCounted):
          del buf[indexToRemoveAt]
    
    return buf
    
  def addTransIfNotFound(self, name):
    """I look for a line in the source (relating to a transform name, ostensibly)
       and if i don't find a matching line, i make it at the botom (but before the
       EOF line, if present), with an indented content of one 'pass'."""
    gotit = False
    for entry in self.fp:
      if entry.strip() == name:
        gotit = True
        break
    if not gotit:
      #?find end of file (scan for first eof OR append blank line and insert there.):
      gotit = False
      for i, entry in enumerate(self.fp):
        if entry.strip() == 'eof':
          gotit = True
          break
      #? if eof isn't found, then append blank line (to be sure there is one) and insert new stuff there
      #? this may be a bit of a hack, but with the XC syntax, gives solid, repeatable results.
      if not gotit:
        self.fp.append('')
        i = len(self.fp)
      self.fp.insert(i, '%s'%name)
      self.fp.insert(i+1, '  pass')
      
  def processSkin(self, filename):
    fp = [string.strip(x) for x in open(filename).readlines()]
    skin = {}
    for entry in fp:
      cleanedLine = entry.strip()
      if not cleanedLine or cleanedLine.startswith('#'):
        continue
      name = cleanedLine.split(' ')[0].strip()
      if not name.startswith('@'):
        raise "In %s, the line '%s' doesn't start with a # or @ (skin variable declaration)"%(name, cleanedLine)
      else:
        name = name[1:]
      arg = ' '.join(cleanedLine.split(' ')[1:]).strip()
      skin[name] = arg
      
    return skin
  
   
#) A collector class that abstracts the insertion of scope close tags and the like when
#) dealing with changing indents in the code. 
class Scopey:
  """  
  Whenever an implicity scoped rule is read from a transform in a transform file both the rule's indent 
  and rule type are noted. If it is needed for a rule's operation a change of scope can be noted and set to precipate
  only when the scope actually closes, instead of being limited to when the rule is run.  A user of this API can 
  choose what rule will be inserted to to inform the runtime that it's supposed to do the work to close a scope. In a sense it 
  just does the typing you wouldn't have wanted to do anyway. this interlinks with both the Parser anad the Parser_Setup 
  since implicit closures are calculated at server (re)load.
  """ 
  
  def __init__(self):
    self.bucket = {}
    self.multi = {}
    self.snapbacks = {}
    self.last = -1
    self.highest = -1
    
  def advance(self, position, rule=False, snapback=False, multi=1):
    """
    given an indentation level, a kind of rule, and optionally a multiplier, I 
    will record that there is a new closure to be performed. When a new scope in a program
    is sent to the withdraw() function that warrents it, the rule given will be returned 
    (multi) times. Usually this number is 1, but a feature of the 'new' rule uses it to 
    create multiple nested scopes (but invisible, syntactically) in the run of one rule.
    """
    if position > self.highest:   
      self.highest = position
    self.bucket[position] = rule
    self.multi[position] = multi
    self.snapbacks[position] = snapback
    pass #dbug( 'Pos: '+`position`+' rule:'+`rule`)
      
  def withdraw(self, position, nextkind=''):
    """
    given an indentation level, I will look for open scopes as recorded by the advance function
    and return [rules] a transform should have appended one by one as a result.
    """
    rulesCollected = []
    if position <= self.highest:
      #get and sort the rules that the new, lesser, indentation orphans (or closes)
      #go backwards, get the reversed order. that's what we want.
      indents = self.bucket.keys()
      indents.sort()
      indents.reverse()
      for scopeLevel in indents:
        #if we are at the current indentation level, we are done:
        if scopeLevel < position: break
        
        #if it's an endif with a following elif/else - then we don't really want a close yet, but we DO
        #want to send a 'snapback' so that the last opened if/elif/else gets the ruledex to 'jump' to
        #appended to it. This mechanism does that - and in doing so, makes dealing with loops much eaiser!
        
        #if it's an endif but the next rule is still a conditional, skip issuing a close, DO issue the jump rule index.
        if self.bucket[scopeLevel] == 'endif' and nextkind.startswith('el'):
          rule = False
        #otherwise send back the appropiate close
        else:
          rule = self.bucket[scopeLevel]
          
        #actually construct the closerule/snapback pair. Note that the code that receives this structure is repsonsible for
        #not doing the given action if it is false (as it is if it isn't provided or needed)
        #this also naturally respects issuing the same close mutliple times as the new rule needs, for instance.
        for i in range(self.multi[scopeLevel]):
          rulesCollected.append([rule, self.snapbacks[scopeLevel]])
          
        #remove the data for that indentation level so nothing is closed more then once, of course. Since
        #all conditionals have an endif, but only the last will be inserted above, there IS something to delete
        #for each run of this loop even if it's unused.
        del self.bucket[scopeLevel]
        del self.multi[scopeLevel]
        del self.snapbacks[scopeLevel]
        
      #mark the newly exposed positon as the highest - all scopes above it have been 'closed' above.
      self.highest = position
      
    pass #dbug('rulescollected: ' + `rulesCollected`)
    return rulesCollected
  
