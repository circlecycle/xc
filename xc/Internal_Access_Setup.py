
# Filename: Internal_Access_Setup.py
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the xc.license file for copyright details.)

#ELEVATED ACCESS SETUP -

#IF A MODULE BY THE KEY NAME IS USED, IT WILL HAVE ACCESS TO THE FOLLOWING INTERNAL
#NAMESPACES ACCESSIBLE THROUGH THE 'ADMIN' ATTRIBUTE


permissions = {
 'admin':
    { 'Instance':['Instance'] },
 'tester':
    { 'library': ['manager', 'library', 'raw'], 'Instance':['Instance'] },
}