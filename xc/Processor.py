

# Filename: Processor.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

# The Process class is passed as input one self.context.tag of the DOM, and to it applies the passed trans 
# representing a single transformation instance. 

import sys, string, re, xml.sax.saxutils, traceback, md5, copy
from xml.dom.minidom import parse, parseString
import Instance, Manager, Config, Parser_Setup
from Utils import dbug_func as dbug
from Utils import IndexShell, ArgvShell, RecurString
import Utils

#import thread

#WARNING - THIS IS A RECURSIVE CLASS. watch out for the TextReplacement function at the bottom, subprossing inside XC happens
#there, not at the for loop in Instance.Request.processXC()

nodegen = parseString('<null/>')

class Process:
  createTextNode = nodegen.createTextNode
  createElement = nodegen.createElement
  setup = Config.setup
  
  #the means to recognize an instance name on a XC call.
  matchSaveNameWithInstance = re.compile( "(\[\w+\]\:\$\%|\%\%)" )
  
  #Singleton for this class to make nodes to be inserted in the dom.
  def __init__(self, req=None, context=None, saveas=False):
    """Given a document node (xml.minidom) and a transform library prepare to process
       any given self.context.tag with any given transform, possibly recursively."""
    self.saveas = saveas
    self.context = context
    self.request = req   #top request
    self.rule = ''
    self.attr = ''
    self.text = ''
    
    self.esc = xml.sax.saxutils.escape
    self.unesc = xml.sax.saxutils.unescape
    
  def processParams(self, params):
    ######## look at the incoming line, do replacement on the instance [x]: if there. If it has a %% prefix then eval
    #         the argument, store it under a dictionary key. that key is put in place in the argument and used later.
    #         This way concrete arguments can be given to subcalls inspite of the nature of xml where the order of 
    #         those calls aren't guaranteed.
    #if they give a python paramerter list invoke the passstack machinery to pass a list to the transform being made.
    passArg = self.matchSaveNameWithInstance.search(params)
    if passArg:
      startdex = passArg.span()[1]
      #make a new entry for this list and record it's key in the param array (tricksty!)
      newhash = "%s"%str(self.request.passstackcounter)
      self.request.passstackcounter += 1
      ptype = params[startdex-2:startdex]
      if params[0] == '[':
        inst = "[%s]:"%self.performTextReplacement(params[1:startdex-4])
      else:
        inst = ""
      try:  
        if ptype == '%%':
          self.request.passstack[newhash] = eval('dict(%s)'%(params[startdex:]), self.context.space.__dict__)
      except:
        raise Exception, "%s: parameter passed as an expression doesn't work: %s."%(self.context.trans.name, params[startdex:])
      params = "%s%s%s"%(inst, ptype, newhash)
      #if they give no argument provide default (for xml compliance reason)
    elif not params.strip(): 
      params = 'true'
    #treat it like a 'normal' comma deliminated simple string..
    else:
      params = self.performTextReplacement(params)
    return params
      
  def applyTransformTo(self, tag):
    """Pass a self.context.tag and a transform to change the DOM accordingly."""
    
    #The heart of the translation process, iterate linearly through
    #the rules in a given transform and execute them on the passed in self.context.tag.
    #it is up to the procedure sending the self.context.tag to poll the correct transform object
    #(there may be many). transforms are created by the parser, if you didn't know.

    #A 'rule' entry looks like: [command, [params,], blocktext], very good thing to know
    pass #dbug('Rules:')
    pass #dbug('\n'.join([`x`+': '+`y` for x, y in enumerate(self.context.trans.rules)]))
    self.ruledex = -1
    ######## OPTIMIZATIONS #################### # # #  #   #    #
    #assign these to local variables to speed up lookup; easy optimization, and clear enough, for now.
    #these are used often enough in a typical transform to warrant the shortcut; some others aren't
    self_context = self.context
    self_context_space = self_context.space
    self_context_currRule = self_context.currRule
    self_context_trans = self_context.trans
    self_context_wrapstate = self_context.wrapstate
    self_context_loopstate = self_context.loopstate
    self_context_loopindexes = self_context.loopindexes
    self_context_space._indexes = self_context.loopindexes
    createTextNode = self.createTextNode
    createElement = self.createElement
    self_request = self.request
    self_request_insertManager_inserttag = self_request.insertManager.inserttag
    self_performTextReplacement = self.performTextReplacement
    self_ruledex = self.ruledex
    self_rule = self.rule
    self_attr = self.attr
    self_text = self.text
    #done with the global->local variable binding speedups.
    #fp = open("/Users/jamesr/test/%s_%s"%(self_ruledex, self.context.trans.name), 'w')
    #fp.write(str(self.context.trans.rules))
    #fp.close()
    
    self_context_space._ = False
    self_context_space.CURRTAG = self_context.tag #the current tag (in the running namespace) is synced here at start (and updated in startwrap rule(s))
    
    while self_ruledex < len(self_context_trans.rules)-1:
      self_ruledex += 1
      self_rule = self_context_trans.rules[self_ruledex]
      self_text = ''
      
      pass #dbug("RULE %s: %s: %s" % (self_ruledex, self_context_trans.name, str(rule)))
      try:
        #extract the info from the rule into values for below, if they are provided
        #by the current rule. (see rule form, above.)
        
        #pretty it up..
        self_context_currRule = self_rule[0]
        if len(self_rule[1]):
          self_attr = self_rule[1][0] #most only have one attr. others read the rule directly
          
        self_text = self_rule[2]
          
#)###### STARTWRAP #################### # # #  # #  #
        #place a temporary self_context.tag in the processing chain, saving the old one.
        #when reversed the nodes on the temp self_context.tag are appended into the original
        if self_context_currRule.startswith('startwrap'):
          self_context_space.CURRTAG = self_context.tag   #update the current tag, if we want it sometime
          if self_context_currRule == 'startwrap' or self_context_currRule == 'startwrapins':
            #if they provide a series of tags to make, synthesize 'em and add to the stack.
            self_text = self_performTextReplacement(self_text)
            tagstomake = self_text.split(',')
            newtags = [x.strip() for x in tagstomake if not x.strip().count(' ')]
            if len(tagstomake) != len(newtags):
              raise Exception, "Error passing arguments to startwrap (plain): %s"%self.esc(self_text) 
            for i, entry in enumerate(newtags):
              newtagtext = '<%s></%s>'%(entry,entry)
              #append the tag to the 'open tag' stack that will get summed back to the main DOM later.
              self_context_wrapstate.append(self_context.tag)
              #The self_context.tag being used for this function is now replaced with a temporary node.
              try:    self_context.tag = parseString('<null>%s</null>'%(newtagtext)).documentElement.firstChild
              except Exception, msg: 
                raise Exception, "Error parsing xml in startwrap (plain): %s"%self.esc(newtagtext)  
              
          elif self_context_currRule == 'startwrapusing' or self_context_currRule == 'startwrapinsusing':
            #just make a transform call on the new node, all using text-construction.
            #also, add the requested module to the 'to be processed list' automatically.
            invokename = self_performTextReplacement(self_rule[1][1])
            tagname = self_performTextReplacement(self_rule[1][0])
            if not invokename.count('.'): 
              modname = self_context_trans.modulename
              invokename = "%s.%s"%(modname, invokename)
            else:
              modname = invokename.split('.')[0]
            if modname not in self_context.modulesToUse: self_context.modulesToUse.append(modname)
            #process a parameter in a way to include the %% flag if present.
            self_text = self.processParams(self_text)
            newtagtext = """<%s %s="%s"></%s>""" %(tagname, invokename, self_text, tagname)
            self_context_wrapstate.append(self_context.tag)
            try:    self_context.tag = parseString('%s'%(newtagtext)).documentElement
            except: raise Exception, "Error parsing xml in startwrap (using) %s"%self.esc(newtagtext)  
              
          elif self_context_currRule.startswith('startwraptext'):
            self_text = self_performTextReplacement(self_text)
            self_attr = self_performTextReplacement(self_attr)
            newtagtext = '<%s>%s</%s>'%(self_attr, self.esc(self_text), self_attr)
            #append the tag to the 'open tag' stack that will get summed back to the main DOM later.
            self_context_wrapstate.append(self_context.tag)
            #The self_context.tag being used for this function is now replaced with a temporary node.
            try:    self_context.tag = parseString('%s'%(newtagtext)).documentElement
            except: raise Exception, "Error parsing xml in startwrap (text) %s"%self.esc(newtagtext)  
              
          elif self_context_currRule.startswith('startwrapset'):
            self_attr = self_performTextReplacement(self_attr)
            newtagtext = '<%s></%s>'%(self_attr,self_attr)
            #append the tag to the 'open tag' stack that will get summed back to the main DOM later.
            self_context_wrapstate.append(self_context.tag)
            #The self_context.tag being used for this function is now replaced with a temporary node.
            try:    self_context.tag = parseString('%s'%(newtagtext)).documentElement
            except: raise Exception, "Error parsing xml in startwrap (set attr) %s"%self.esc(newtagtext)  
            currentVal = self_context.tag.getAttribute(self_rule[1][1])
            self_context.tag.setAttribute(self_rule[1][1], self_performTextReplacement(self_text)+currentVal)    
            
          elif self_context_currRule.startswith('startwrapattr'):
            self_attr = self_performTextReplacement(self_attr)
            newtagtext = '<%s></%s>'%(self_attr,self_attr)
            #append the tag to the 'open tag' stack that will get summed back to the main DOM later.
            self_context_wrapstate.append(self_context.tag)
            #The self_context.tag being used for this function is now replaced with a temporary node.
            self_context.tag = parseString('%s'%(newtagtext)).documentElement
            #raise Exception, "Error parsing xml in startwrap (attr)"
            #put the attributes request on the tag
            try:
              toadd = eval(self_text, self_context_space.__dict__)
            except Exception, msg:
              raise Exception, "Name: %s using attr rule %s has errors: %s"%(self_context_trans.name, self_text, str(msg))
            for entry in toadd.keys():
              self_context.tag.setAttribute(entry, str(toadd[entry]))    
              
          elif self_context_currRule.startswith('startwrapinit'):
            #append the tag to the 'open tag' stack that will get summed back to the main DOM later in
            #a different place then we are now - in effect providing initialization nodes.
            #only do this on a 'unique' transform if it's not in the uniqueHeadTracker
            if 'unique' in self_context_currRule:
              #if it's the 'on' varient - use that as the key
              if self_context_currRule.endswith('on'):
                key = self_performTextReplacement(self_attr)
              #else refer to the specific rule in it's specific location
              else:
                key = "%s%s"%(self_context_trans.name,self_ruledex)
              #see if it's been done - if so, jump to next block
              if self_request.uniqueHeadTracker.has_key(key): 
                self_ruledex = int(self_rule[-1])
                continue
              else: 
                self_request.uniqueHeadTracker[key] = True
            #make a new node in preparation for a new block
            self_context_wrapstate.append(self_context.tag)
            self_context.tag = parseString('<null></null>').documentElement
              
          elif self_context_currRule.startswith('startwrapxml'):
            self_attr = self_performTextReplacement(self_attr)
            newtagtext = '<%s></%s>'%(self_attr, self_attr)
            #append the tag to the 'open tag' stack that will get summed back to the main DOM later.
            self_context_wrapstate.append(self_context.tag)
            #The self_context.tag being used for this function is now replaced with a temporary node.
            try:    self_context.tag = parseString('<null>%s</null>'%(newtagtext)).documentElement.firstChild
            except: raise Exception, "Error parsing xml in startwrap (xml) %s"%self.esc(newtagtext)  
            #make a new xml fragment to add to the new tag
            self_text = self_performTextReplacement(self_text)
            try:  textXML = parseString('<null>%s</null>'%(self_text)).documentElement.childNodes
            except: raise Exception, "Error parsing xml in startwrap (xml) %s"%self.esc(self_text)  
            self_context.tag_appendChild = self_context.tag.appendChild
            [self_context.tag_appendChild(node.cloneNode(deep=True)) for node in textXML]
            
          elif self_context_currRule.startswith('startwrapprint'):
            self_attr = self_performTextReplacement(self_attr)
            newtagtext = '<%s></%s>'%(self_attr, self_attr)
            #append the tag to the 'open tag' stack that will get summed back to the main DOM later.
            self_context_wrapstate.append(self_context.tag)
            #The self_context.tag being used for this function is now replaced with a temporary node.
            try:    self_context.tag = parseString('<null>%s</null>'%(newtagtext)).documentElement.firstChild
            except: raise Exception, "Error parsing xml in startwrap (print) %s"%self.esc(newtagtext)  
            #make a new pre fragment to add to the new tag
            pretag = createElement('pre')
            pretag.appendChild(createTextNode(self_performTextReplacement(self_text)))
            self_context.tag.appendChild(pretag)   
          continue
          
#)###### ENDWRAP #################### # # #  # #  #

        #execute a wrap operation. use the open and close information 
        #provided in self.wrapstate
        elif self_context_currRule.startswith('endwrap'):
          #append end html, concatenate start, middle, and end. then run it through the processor
          #to get text replacement on the start/end chunks. re-processing the middle is unavoidable
          #but means less since there is nothing to replace in it by this point...
          if len(self_context_wrapstate) == 0:
            raise Exception, "close of a wrap without matching beginning, rules are: %s"%(`[x[0] for x in self_context_trans.rules]`)
          
          fullxml = self_context.tag.toxml()
          
          fullxml = self_performTextReplacement(fullxml, subProcess=True)
          try:    newtaglist = parseString('<null>%s</null>'%fullxml).documentElement.childNodes
          except: raise Exception, "Error parsing xml in an endwrap %s"%self.esc(fullxml)  
          
          self_context.tag = self_context_wrapstate.pop()
          if self_context_currRule == "endwrapinsert":
            [self_request_insertManager_inserttag(self_context.tag, x.cloneNode(deep=True)) for x in newtaglist]
          else:
            self_context.tag_appendChild = self_context.tag.appendChild
            [self_context.tag_appendChild(x.cloneNode(deep=True)) for x in newtaglist]
          continue
          
#)###### SETATTR #################### # # #  # #  #

        elif self_context_currRule == 'setattr':
          self_context.tag.setAttribute(self_attr, self_performTextReplacement(self_text))
          continue
          
#)###### ADDTEXT #################### # # #  # #  #

        elif self_context_currRule == 'addtext':
          textnode = createTextNode(self_performTextReplacement(self_text))
          self_context.tag.appendChild(textnode)
          continue
          
#)###### ADDXML #################### # # #  #   #  #

        elif self_context_currRule == 'addxml':
          buf = self_performTextReplacement(self_text, subProcess=True).strip()
          try: textXML = parseString('<null>%s</null>'%buf).documentElement.childNodes
          except: raise Exception, "Error parsing xml in an addxml command %s"%self.esc(buf) 
          self_context.tag_appendChild = self_context.tag.appendChild
          [self_context.tag_appendChild(node.cloneNode(deep=True)) for node in textXML]
          continue
          
#)###### PYTHON #################### # # #  #   #  #

        #Don't preprocess the block that goes to python script - 
        # not that it makes sense anyway.. We don't want a malcrafed URL to somehow run code, for instance.
        elif self_context_currRule == 'python':
          #run the user code -- any exceptions should use the exception handler
          #defined on the transform, if one is given.
          #run their code
          exec self_text in self_context_space.__dict__   
          continue
          
#)####### ENDLOOP ############################### # # #  #   #  #
          
        elif self_context_currRule.startswith('endloop'):
          #increment counter
          self_context_loopindexes[-1] += 1
          obj, snapback, self_attr = self_context_loopstate[-1]
          index = self_context_loopindexes[-1]
          if index < len(obj):
            self_context_space._i = IndexShell(index).setlist(self_context_loopindexes)
            setattr(self_context_space, self_attr, obj[index])
            self_ruledex = snapback
          else:
            self_context_loopstate.pop()
            self_context_loopindexes.pop()
          continue
          
#)###### PRINT #################### # # #  # #  #

        elif self_context_currRule == 'print':
          pretag = createElement('pre')
          pretag.appendChild(createTextNode(self_performTextReplacement(self_text)))
          self_context.tag.appendChild(pretag)
          continue


#)###### IF #################### # # #  # #  #

        elif self_context_currRule == 'if':
          #push a new if state marker on the stack
          self_context.lastConditionState.append('')
          if eval(self_text, self_context_space.__dict__):
            self_context.lastConditionState[-1] = 'foundmatch'
          else:
            self_ruledex = self_context_trans.rules[self_ruledex][3]-1
          continue         
            
#)###### ELIF and ELIFNOT #################### # # #  #   #  #

        elif self_context_currRule == 'elif':
          if self_context.lastConditionState[-1] == 'foundmatch':
            self_ruledex = self_context_trans.rules[self_ruledex][3]-1
          elif eval(self_text, self_context_space.__dict__):
            self_context.lastConditionState[-1] = 'foundmatch'
          else:
            self_ruledex = self_context_trans.rules[self_ruledex][3]-1
          continue
            
#)###### ELSE #################### # # #  #   #  #

        elif self_context_currRule == 'else':
          if self_context.lastConditionState[-1] == 'foundmatch':
            self_ruledex = self_context_trans.rules[self_ruledex][3]-1
          else:
            self_context.lastConditionState[-1] = 'foundmatch'
          continue  
          
#)###### END IF #################### # # #  #   #  #

        elif self_context_currRule == 'endif':
          self_context.lastConditionState.pop()
          continue
          
#)####### LOOP #################### # # #  #   #  #

        elif self_context_currRule.startswith('loop'):
          obj = eval(self_text, self_context_space.__dict__)
          #if the loop is null to start with then skip the loop entirely, including the close
          if not obj:
            self_ruledex = self_context_trans.rules[self_ruledex][3]
            continue
          try:
            #deal with the first form of the command
            if self_context_currRule == 'loop':
              attrToSet = self_performTextReplacement(self_attr)
              self_context_loopstate.append([obj, self_ruledex, attrToSet])
              self_context_loopindexes.append(0)
              setattr(self_context_space, attrToSet, obj[0])
            
            #deal with the second form - given that the start wrap command is already properly inserted by the parser.
            elif self_context_currRule == 'loopusing':
              attrToSet = self_performTextReplacement(self_rule[1][1])
              self_context_loopstate.append([obj, self_ruledex, attrToSet])
              self_context_loopindexes.append(0)
              setattr(self_context_space, attrToSet, obj[0])
          except:
            raise Exception, "Non iterable object in loop commmand."
            
          self_context_space._i = IndexShell(0).setlist(self_context_loopindexes)
          continue

#)###### PREPEND #################### # # #  # #  #

        elif self_context_currRule == 'prepend':
          currentVal = self_context.tag.getAttribute(self_attr)
          self_context.tag.setAttribute(self_attr, self_performTextReplacement(self_text)+currentVal)
          continue
          
#)###### ATTRS #################### # # #  #   #  #

        elif self_context_currRule == 'attr': 
          try:
            toadd = eval(self_text, self_context_space.__dict__)
          except Exception, msg:
            raise Exception, "Name: %s using attr rule %s has errors: %s"%(self_context_trans.name, self_text, str(msg))
          for entry in toadd.keys():
            self_context.tag.setAttribute(entry, str(toadd[entry]))
          continue
  
#)###### INSERTTEXT #################### # # #  #   #  #

        elif self_context_currRule == 'inserttext':
          textnode = createTextNode(self_performTextReplacement(self_text))
          self_request_insertManager_inserttag(self_context.tag, textnode)  
          continue

#)###### SETTEXT #################### # # #  # #  #

        elif self_context_currRule == 'settext':
          while 1:
            if not self_context.tag.childNodes: break
            self_context.tag.removeChild(tag.firstChild).unlink()
          textnode = createTextNode(self_performTextReplacement(self_text))
          self_context.tag.appendChild(textnode)
          continue

#)###### INSERTXML #################### # # #  # #  #

        elif self_context_currRule == 'insertxml':
          buf = self_performTextReplacement(self_text, subProcess=True)
          xmlToLoad = '<null>%s</null>\n'%buf
          try: textXML = parseString(xmlToLoad).documentElement.childNodes
          except: raise Exception, "Error parsing xml in insertxml %s"%self.esc(xmlToLoad) 
          #[self_context.tag.insertBefore(node.cloneNode(deep=True), self_context.tag.firstChild) for node in textXML]
          [self_request_insertManager_inserttag(self_context.tag, node.cloneNode(deep=True)) for node in textXML] 
          continue
          
#)###### RETURN #################### # # #  #   #  #

        elif self_context_currRule == 'return':
          #if we want to exit the loop then there may be open wraps outstanding. 
          #Close them and return, as logically desired.
          #this is copied pretty much verbatim from the endwrap block, above
          self_context_wrapstate.reverse()
          for tag in self_context_wrapstate:
            fullxml = self_context.tag.toxml()
            fullxml = self_performTextReplacement(fullxml, subProcess=True)
            try:    newtag = parseString(fullxml).documentElement
            except: raise Exception, str("Error parsing xml in close of transform: %s"%self.esc(fullxml))
            self_context.tag = self_context_wrapstate.pop()
            if self_context_currRule == "endwrapinsert":
              self_request_insertManager_inserttag(self_context.tag, newtag)
            else:
              self_context.tag.appendChild(newtag)

          #run the command to remove the attribute from the calling node IF it has one:
          if self_context_trans.kind not in Parser_Setup.transformsWithoutAttrToRemove:
            self_ruledex = len(self_context_trans.rules)-2
            continue
          else:
            break

#)###### INIT #################### # # #  #   #  #

        elif self_context_currRule.startswith('init'): 
          #?add the builtup dom in wrapstate to the top or bottom of the dom 
          #?according to taste. html doesn't need this, but other xml languages do.    
          if self_context_currRule.endswith('wrap'):
            if 'bottom' in self_context_currRule:
              [self_request.dom.documentElement.firstChild.appendChild(x) for x in self_context.tag.childNodes]
            else:
              [self_request_insertManager_inserttag(self_request.dom.documentElement.firstChild, x.cloneNode(deep=True))
                for x in self_context.tag.childNodes]
            self_context.tag = self_context_wrapstate.pop()
            continue
            
          #?do the text block munging for the special script and style tag types from here down
          elif self_context_currRule.startswith('initunique'):
            key = "%s%s"%(self_context_trans.name,self_ruledex)
            if not self_request.uniqueHeadTracker.has_key(key):
              self_request.uniqueHeadTracker[key] = True
            else: 
              continue
              
          #?If in normal mode, not compiling for laszlo.
          if self_request.switchLaszloForFlash:
            try:
              if self_context_currRule == 'initbottom':
                targettag = self_request.dom.documentElement.getElementsByTagName('body')[0]
              else:
                targettag = self_request.dom.documentElement.getElementsByTagName('head')[0]
            except:
              targettag = self_request.dom.documentElement
          else:
            #?else laszlo is always the firstChild as root.
            targettag = self_request.dom.documentElement.firstChild
            
          newtagName = self_attr
          tagtype = None
          if self_request.switchLaszloForFlash:
            if newtagName == 'script':  tagtype = 'text/javascript'
            elif newtagName == 'style': tagtype = 'text/css'

          prefix = ""
          if self_context_currRule == 'initbottom':
            prefix = 'POST'
          idfortag = 'XC_%s%s'%(prefix,newtagName)

          newtag, inPlace = None, False
          for node in targettag.getElementsByTagName(newtagName):
            if node.getAttribute('id') == idfortag:
              newtag = node
              inPlace = True
              break
          if not newtag:
            newtag = createElement(newtagName)
            if tagtype:  newtag.setAttribute('type', tagtype)
            newtag.setAttribute('id', idfortag)

          buf = self.esc(self_performTextReplacement(self_text))
          innertext = createTextNode(buf)
          newtag.appendChild(innertext)
          if not inPlace:
            if self_context_currRule == 'initbottom':
              targettag.appendChild(newtag)
            else:
              self_request_insertManager_inserttag(targettag, newtag.cloneNode(deep=True))
          continue
          
#)###### REMOVE #################### # # #  #   #  #

        elif self_context_currRule == 'remove':
          if self_text != '': 
            self_text = self_performTextReplacement(self_text)
            for entry in [x.strip() for x in self_text.split(',')]:
              if self_context.tag.hasAttribute(entry):
                self_context.tag.removeAttribute(entry)
          continue
        
#)###### CALL #################### # # #  # #  #
        elif self_context_currRule.startswith('call'):
          #process a text block in a way to make a parameter string, incl. the %% flag if present.
          self_text = self.processParams(self_text)
          #look at the param
          self_attr = self_performTextReplacement(self_attr).split('.')
          if len(self_attr) > 2:
            newtagtext = """<%s %s="%s"/>"""%(self_attr[1], "%s.%s"%(self_attr[0], self_attr[2]), self_text)
            newtagtype = "%s.%s"%(self_attr[0], self_attr[2])
          else:
            newtagtext = """<call %s="%s"/>"""%('.'.join(self_attr), self_text)
            newtagtype = "call.%s"%(self_attr[1])
          #cool, construct the tag and send!
          try:
            self.request.processFragment(newtagtext, [self_attr[0]], scansingle=newtagtype, saveas=self_context.saveas)
            self.context.setSpaceForTag()
          except Exception, msg:
            raise "Trans: %s, rule %s: attr: %s, Problem in CALL command: %s"%(self_context_trans.name, self_ruledex, `self_attr`, str(msg))
          continue
          
#)###### APPEND #################### # # #  #   #  #

        elif self_context_currRule == 'append':
          currentVal = self_context.tag.getAttribute(self_attr)
          self_context.tag.setAttribute(self_attr, currentVal+self_performTextReplacement(self_text))
          continue
          
#)###### EVALUATE #################### # # #  #   #  #

        #?take an expression, use text replacement ONLY for autonaming, and set the given
        #?variable to the resulting value in the current namespace
        elif self_context_currRule == 'evaluate':
          self_attr = self_performTextReplacement(self_attr)
          self_text = self_performTextReplacement(self_text, namesonly=True)
          setattr(self_context_space, self_attr, eval(self_text, self_context_space.__dict__))
          continue

#)###### PASS #################### # # #  #   #  #
        elif self_context_currRule == 'pass':
          continue

#)###### CONTEXT #################### # # #  #   #  #
        elif self_context_currRule == 'context':
          self_context.tag = eval(self_text, self_context_space.__dict__)
          continue

#)###### READ #################### # # #  #   #  #

        elif self_context_currRule == 'read':
          contents = []
          contents_append = contents.append
          for x in self_context.tag.childNodes:
            if x.nodeType == x.TEXT_NODE: 
              contents_append(x.nodeValue)
            else: 
              contents_append(x.toxml())
          contents = ''.join(contents)
          setattr(self_context_space, self_attr, contents)
#?copied from 'erase'
          self_context_abandonedTags_append = self_context.abandonedTags.append
          self_context.tag_removeChild = self_context.tag.removeChild
          while 1:
            if not self_context.tag.childNodes: break
            self_context_abandonedTags_append(self_context.tag_removeChild(self_context.tag.firstChild))
          continue
          continue
          
#)######## BINARY #################### # # #  #   #    #

        elif self_context_currRule == 'binary':
          self_request.binary = self_performTextReplacement(self_text)
          continue

#)###### ERASE (contents of the current tag)#################### # # #  # #  #

        elif self_context_currRule == 'erase':
          self_context_abandonedTags_append = self_context.abandonedTags.append
          self_context.tag_removeChild = self_context.tag.removeChild
          while 1:
            if not self_context.tag.childNodes: break
            self_context_abandonedTags_append(self_context.tag_removeChild(self_context.tag.firstChild))
          continue

#)###### IMPORT #################### # # #  #   #  #

        elif self_context_currRule == 'import':
          #add a module name to the list of modules to be processed
          #when considering rules that could have recursive XC xml calls in them.
          buf = self_performTextReplacement(self_text)
          [self_context.modulesToUse.append(x) 
            for x in [x.strip() for x in buf.split(',')] 
              if x not in self_context.modulesToUse]
          continue

#)###### CLEAR IMPORTS #################### # # #  # #  #

        elif self_context_currRule == 'clearimp':
          #Clear any modules that are marked for subprocessing
          self_context.modulesToUse = []
          continue

#)###### LOADUNIQUE #################### # # #  #   #  #

        elif self_context_currRule == 'loadunique':
          scriptname = self_performTextReplacement(self_text)
          tagis = self_attr
          if not self.request.uniqueFilesLoaded.has_key(scriptname):
            try: targettag = self.request.dom.documentElement.getElementsByTagName('head')[0]
            except: continue #if we can't get the DOM, the we either aren't in the main doc's dom or there is something else we don't wanna touch..
            self.request.uniqueFilesLoaded[scriptname] = True
            tagtype = 'text/javascript'
            if tagis in ('style', 'link'):  
              tagtype = 'text/css'
            newtag = createElement(tagis)
            newtag.setAttribute('type', tagtype)
            if tagis in ('script', 'style'):
              newtag.setAttribute('src', self.setup.serverUrl+scriptname)
              newtag.appendChild(createTextNode(''))
            elif tagis == 'link':
              newtag.setAttribute('href', self.setup.serverUrl+scriptname)
              newtag.setAttribute('rel', 'StyleSheet')
            self_request_insertManager_inserttag(targettag, newtag)
          pass #dbug("loaded script: " + scriptname +': '+`self.request.uniqueFilesLoaded`)
          continue

#)###### OVERLAY #################### # # #  # #  #
        elif self_context_currRule == 'overlay':
          #the point here is to take the tag (treating it as a sub-dom)
          #and passing to to be XC-subprocessed using functions advertised in the request class. 
          #The text argments are placed into the tag as parameters to process that would ordinarily 
          #go to in the attribute when invoking as xml. this means that overlayable transforms have 
          #to rely on just this attribute, or at least an agreement on what attributes will be present..
          
          #get the module, tag type and processing module to use
          if not self_attr.count('.'): 
            self_attr = "%s.%s"%(self_context_trans.modulename, self_attr)
          mod, name = self_attr.split('.')
          ttype = self_context.tag.tagName
          #try:
          if mod not in self_context.modulesToUse: self_context.modulesToUse.append(mod)
          
          #raise Exception, `self_context.modulesToUse`
          #dummy check:
          if not Manager.manager.library.raw.has_key(mod): raise Exception, "Overlay instruction didn't find the requested module: %s"%mod
          if not Manager.manager.library.raw[mod].has_key('%s.%s'%(ttype,name)): raise Exception, "TAG.NAME = %s.%s" % (ttype,name) + "<br/> Modules' keys: " + `Manager.manager.library.raw[mod].keys()`+"<br/><br/>Overlay instruction didn't find the requested transform."
            
          #process a parameter in a way to include the %% flag if present.
          self_text = self.processParams(self_text)
                    
          #process the dom chunk as given, using the modules given.
          self_context.tag.setAttribute('%s.%s'%(mod,name), self_text)
          self.request.processXC([mod],chunk=self_context.tag, scansingle="%s.%s"%(ttype,name), saveas=self_context.saveas)
          #insert into the DOM tree.
          #newelem = self_context.tag.parentNode.insertBefore(chunk.cloneNode(deep=True), self_context.tag)
          #erase the pre-transformed tag, and make the current tag in it's place
          #self_context.tag.parentNode.removeChild(self_context.tag).unlink()
          self_context.setSpaceForTag()
          continue

#)###### EXCEPTION HANDLER #################### # # #  # #  #          

      #handle the except clause(s), if nescessary
      #they can specify a number of except clauses, the first one to work wins.    
      except Exception, msg:      
        
        #debug mode. simple.
        if Config.setup.debugmode[0].lower() == 't':
          raise
          #raise Exception, str('%s: rule: %s, is %s, %s\nmsg: %s'%(self_context_trans.name, self_ruledex, self_rule, str(msg)))
        
        #if they were in a wrap clause, the current self_context.tag was temporary. make it the real one
        if self_context_wrapstate:
          self_context.tag = self_context_wrapstate[0]   #the original self_context.tag on the active DOM.  
        
        caught = False
        
        if not self_context_trans.errorHandler:
          import sys  
          #if not caught then replace the whole tranform with a traceback
          if self_context.tag.childNodes:
            [self_context.tag.removeChild(x).unlink() for x in self_context.tag.childNodes]
            
          message = "<pre>Error at %s, line %s: %s, rule is %s TRACEBACK: %s</pre>"%\
            (self_context_trans.name, 
            self_ruledex, 
            self.esc(`msg`), 
            self.esc(`self_rule`),
            self.esc(''.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))))
          self_context.tag.appendChild(parseString(message).documentElement)
          #raise
        else:
          #otherwise iterate through the except blocks -- if one blows continue on to the next.
          #if they all blow, complain in a full raise.
          for handler in self_context_trans.errorHandler:
            try:
              import sys
              self_context.perTransform(handler)
              self_context.perTag(tag)
              self_context_space._errmsg = self.unesc(str(msg))
              self_context_space._errloc = self_context_trans.name
              self_context_space._err = self_context_trans.name+': '+ self.unesc(str(msg))+string.replace('Traceback: \n'+'\n'.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)), '\n', '<br/><br/>')
              self.applyTransformTo(tag)
              caught = True  #we got one
              break
            except: 
              pass
          if not caught:
            raise
        
        #if the exception was handled - break - why? because we don't
        #want to render any more of the transform.
        break #break for production!!!
    
    #remove 'abandoned' tags (element objects that the 'clear' rule has erased during one transform run.
    #Often a clear command is used to begin the layout proper of a transform, but having to explitcly 
    #store configuration markup from DOM into local variables is too much to ask for when it's already there,
    #sitting in memory. Since Minidom doesn't actually erase until an unlink() call, it won't show when rendered 
    #but still be accessible by dom calls for logical use. cool!
    [node.unlink() for node in self_context.abandonedTags]

      
      
  def performTextReplacement(self, origText, subProcess=False, namesonly=False, allowSubprocessing=False):
    """performTextReplacement performs text replacement to conform to the <!some_var!> syntax. It
       pulls from an xml.minidom object to do this, so it just needs the caught self.context.tag to determine
       new values. 
    """
    global esc
    #get the namespace the transform is run in
    #use a regex to find vars to replace:
    outputText = origText
    processList = []
    #each time it finds a match record it's location (and extract interior to)
    #a processing list to consider in the next block. no match means it 'll skip the next loop.
    #i just got down with regexs again, so i think i'll be updating this soon.
    Instance_matchTextVar_search = Instance.matchTextVar.search
    self_context_space = self.context.space
    preCompiles = Manager.manager.preCompiles
    while 1:
      match = Instance_matchTextVar_search(origText)
      if not match: break
      x, y = match.span()
      fullvartext = origText[x:y]
      attrToReplace = origText[x+2:y-2]
      toreplace = [fullvartext, attrToReplace]
      if toreplace not in processList:
        processList.append(toreplace)
      origText = origText[y:]
    
    #else begin replacment of variables
    self_context_space___dict__ = self_context_space.__dict__
    for entry in processList:
      fullvartext, attrToReplace = entry
      #?possibly search the stack 'history' for other transforms' autonames on \@+\w+
      if attrToReplace[0] == '@':
        newstring, index = "", 0
        while index < len(attrToReplace) and attrToReplace[index] == '@': 
          index += 1
        #this is because just the @@'s may exist, so the string remains blank if only @@ are there 
        if len(attrToReplace)-1 > index: 
          newstring = attrToReplace[index:]
        outputText = outputText.replace(fullvartext, "%s%s_PUB"%(self_context_space.AUTO[-index], newstring)) 
        continue
      #?other autoname markers *without* history detection:
      elif attrToReplace.startswith('.'):
        if attrToReplace.startswith('..'):
          attrToReplace = attrToReplace[2:]
          #another mods namespace? or not?
          if '.' in attrToReplace:  mod, attrToReplace = attrToReplace.split('.')
          else:                     mod = self_context_space.MOD
          outputText = outputText.replace(fullvartext, "%s_%s"%(mod, attrToReplace))
        else:
          attrToReplace = attrToReplace[1:]
          outputText = outputText.replace(fullvartext, "%s_%s"%(self_context_space.AUTO[-1], attrToReplace)) 
        continue
      if namesonly: raise Exception, 'A python expression is being used inside of a textreplacement intended to evaluate autonaming statements only'
      #okay, i've done this several (larger) ways, but let's just settle on a '?' operator for default goodness. all else should
      #be python eval strings. at one point there was a whole sub-language here, but that is prolly a confusing scene.
      if attrToReplace[0] == '?':
        buf = attrToReplace[1:].split('|')
        attrgiven = buf[0].strip()
        if len(buf) < 2: raise Exception, 'The ? operator needs two arguments seperated by a pipe \'|.'
        tmp = eval(preCompiles[attrgiven], self_context_space___dict__)
        if not tmp:
          defaultArg = buf[1].strip()
          tmp = eval(preCompiles[defaultArg], self_context_space___dict__)
        outputText = outputText.replace(fullvartext, str(tmp))
        continue
      #?
      elif attrToReplace[0] == '$':
        trans = self.context.trans
        Skins = Manager.manager.library.Skins
        try:
          outputText = outputText.replace(fullvartext, Skins[trans.modulename][str(attrToReplace[1:])])
        except Exception, msg:
          raise "In the transform %s, module %s, the skin variable %s doesn't exist. %s"%(trans.name, trans.modulename, str(attrToReplace[1:]), Skins[trans.modulename])
        continue
      #?a simple shortcut to escaping text
      elif attrToReplace[0] == '%':
        value = eval(preCompiles[attrToReplace[1:]], self_context_space___dict__)
        outputText = outputText.replace(fullvartext, self.esc(str(value))) 
        continue
      #?Default: retrieve then eval() a value from the space associated with the transform.
      try:
        value = eval(preCompiles[attrToReplace], self_context_space___dict__)
        outputText = outputText.replace(fullvartext, str(value)) 
      except Exception, msg:
        raise Exception, "at '%s', the expression [~%s~] doesn't work: %s"%(outputText, attrToReplace, str(msg))
      continue
      
    pass #dbug("text after text replacement:\n"+outputText+"---")
    #also, remove any [~~] block pairs remaining. There shouldn't be - and this prevents a hole where by content could get
    #evaluated as python expressions in some circumstances. Since ~] is rare anyway, seeing it as -] should get the point across, methinks.
    #i could, on the last swing, search and replace them back to ~] or something, but that hardly seems worth it, and the security
    #gain surely is.
    if not allowSubprocessing:
      outputText = outputText.replace('~]', '-]')
    #Done! toss the output back... except, OH BTW, here is the recursive magic in XC - hand it to itself to
    #run again if an xml block or otherwise block should be so scanned!
    if len(self.context.modulesToUse) > 0 and subProcess:
      pass #dbug('\nIm about to subprocess a %s directive' % self.context.currRule.upper())
      outputText = self.request.processFragment(outputText, self.context.modulesToUse, saveas=self.context.saveas)
      #after processing other tags, the variables in the current namespace might have changed. So,
      #set them back to the tag we were in the middle of processing when we left to recurse.
      self.context.setSpaceForTag()
      return outputText
    else:
      return outputText

  

# a simple little thing to track inserted nodes - we want nodes to go on top but NOT above 
#tags inserted as directive earlier, preserving the way the code looks to the user. (kinda like a 
#stack we don't want to read it LIFO but FIFO!)
class InsertTracker:
  """make a little class to handle counting inserted tags within a request.
    it will auto increment through a series of inserted nodes and always insert 
    after them - not the absolute insert we otherwise have. It does this
    by keying on the incoming 'base' tag to insert into - all inserts to that
    node during the life of this object will be added in logical sequence, barring
    other activity from DOM-meddling functions elsewhere..
  """
  def __init__(self):
    self.tagTracker = {}

  def inserttag(self, tag, newtag):
    tagid = id(tag)
    if not self.tagTracker.has_key(tagid):
      if tag.childNodes == []:  tag.appendChild(newtag)
      else:                     tag.insertBefore( newtag, tag.firstChild )
      self.tagTracker[tagid] = newtag
    else:
      tag.insertBefore( newtag, self.tagTracker[tagid].nextSibling )
      self.tagTracker[tagid] = newtag
      
      
