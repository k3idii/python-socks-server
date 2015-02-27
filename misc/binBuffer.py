from StringIO import StringIO
import struct
import string
import os

CHUNK_SIZE = 1024

def glue(parts,delim='',preproc=None):
  if preproc:
    for fn in preproc:
      parts = map( fn , parts )
  return delim.join(parts)

def unpackEx(fmt,data,into=None):
  t = struct.unpack(fmt,data)
  if not t :
    return None
  if not into:
    return t
  if len(t) != len(into):
    raise Exception("readFmt into values : size mismatch [%d != %d]" % (len(into),len(t)))
  return dict( (into[i],t[i]) for i in range(len(into))  )  


class bufferException(Exception):
  pass


class extStringIO(StringIO):  
  def readN(self,n):
    d = self.read(n)
    if not d or len(d) < n:
      raise bufferException("Read error : need %d bytes, got %d " % ( n , len(d) ))
    return d
   
  def readFmt(self,fmt="",into=None):
    n = struct.calcsize(fmt)
    d = self.readN(n)
    return unpackEx(fmt,d,into) 

  def readFmtSingle(self,fmt):
    v = self.readFmt(fmt)
    if v:
      return v[0]
    else:
      return None

  def readRest(self):
    s = self.getLen()
    p = self.getPos()
    d = s - p
    return self.readN(d)
 
  def append(self,data):
    p = self.tell()
    self.seek(0, os.SEEK_END)
    self.write( data )
    self.seek(p)

  def appendFmt(self,fmt,*a):
    return self.append(struct.pack(fmt, *a) )

  def writeFmt(self,fmt,*a):
    return self.write( struct.pack(fmt , *a) )
  
  def readAll(self):
    p = self.tell()
    self.seek(0)
    v = self.read()
    self.seep(p)
    return v

  def dump(self):
    return self.getvalue()

  def getLen(self):  
    org = self.tell()
    self.seek(0, os.SEEK_END)
    end = self.tell()
    self.seek(org)
    return end

  def getPos(self):
    return self.tell()
  
  def available(self):
    return self.getLen() - self.getPos()

  def hexDump(self,inRow=16,title=None,head=True):
    S = ' \n'
    if head:
      if title:
        S += " .----[ %s ]----- \n" % title
      S += "| offset          ascii                 hex   \n"
    p = self.tell() # save 
    self.seek(0)    # rewind
    fmt = "| 0x%08X %-"+str(inRow)+"s \t %s\n"
    while True:
      of = self.tell()
      chunk = self.read(inRow)
      hx = ''
      ch = ''
      for c in list(chunk):
        ch+= c if ord(c)>=32 and ord(c)<127 else '.'
        hx += "%02X " % ord(c)
      S += fmt % (of,ch,hx)
      if len(chunk) < inRow:
        break
    S+= "| 0x%08X \n" % self.tell()
    S+= "`-- \n"
    self.seek(p)
    return S


class _buffer:
  pass



class StringIO_buffer(_buffer):
  
  def setup(self):
    pass

  def readFunc(self,size=1024):
    pass






