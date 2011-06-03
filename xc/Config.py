
# Filename: Config.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

import sys, Utils

######## Configuration Reading #################### # # #  #   #    #

#The only path that needs to be set in the codebase to get the rest of the system up.
setupFile = "/etc/XCConfig.xml" 


####all boilerplate past here...

#scan the plist and load the resulting string vars into setup
setup = Utils.PlistParser(setupFile)

#put in some slashies if they are missing..
if setup.baseUrl[-1] != '/':
  setup.baseUrl = setup.baseUrl + '/'
  
if setup.basePath[-1] != '/':
  setup.basePath = setup.basePath + '/'
  
#if setup.zopePath[-1] != '/':
#  setup.zopePath = setup.zopePath + '/'

#these are computed instead of specified because they would be redundant 
#to include in the config plist, since we have enough info to construct them.
#not wise to change this part.
if setup.serverPrefix.lower() != 'none':
  setup.serverPath = '/' + setup.serverPrefix + '/'
  setup.serverUrl = setup.baseUrl + setup.serverPrefix + '/'
else:
  setup.serverPath = '/'
  setup.serverUrl = setup.baseUrl+ '/'
  
#make the comma delim user list into a true list, mthese user names are allowed
#to restart, reload the server remotely.
setup.sudoers = [x.strip() for x in setup.sudoers.split(',')]

#setup the external python module path that XC uses..
sys.path.append(setup.commonPyPath)
