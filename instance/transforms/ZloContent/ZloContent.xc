
# Filename: ZloContent.bloom
# Copyright: 2005-2007 James Robey
# Project: XC (please reference the XC.license file for copyright details.)

server content.getFile
  py
    path = "%s_content/%s"%(THISPATH, '/'.join(ARGP))
    content = open(path).read()
  text [~content~]
