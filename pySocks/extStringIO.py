from StringIO import StringIO
import struct
import os

CHUNK_SIZE = 1024


def glue(parts, delim='', preproc=None):
  if preproc:
    for fn in preproc:
      parts = map(fn, parts)
  return delim.join(parts)


def unpack_ext(fmt, data, into=None):
  t = struct.unpack(fmt, data)
  if not t:
    return None
  if not into:
    return t
  if len(t) != len(into):
    raise Exception("unpack into values : size mismatch [%d != %d]" % (len(into), len(t)))
  return dict((into[i], t[i]) for i in range(len(into)))


class BufferException(Exception):
  pass


class extStringIO(StringIO):
  def read_n(self, n):
    d = self.read(n)
    if not d or len(d) < n:
      raise BufferException("Read error : need %d bytes, got %d " % (n, len(d)))
    return d

  def readFmt(self, fmt="", into=None):
    n = struct.calcsize(fmt)
    d = self.read_n(n)
    return unpack_ext(fmt, d, into)

  def readFmt_single(self, fmt):
    v = self.readFmt(fmt)

    if v:
      return v[0]
    else:
      return None

  def read_rest(self):
    s = self.get_len()
    p = self.get_pos()
    d = s - p
    return self.read_n(d)

  def append(self, data):
    p = self.tell()
    self.seek(0, os.SEEK_END)
    self.write(data)
    self.seek(p)

  def appendFmt(self, fmt, *a):
    return self.append(struct.pack(fmt, *a))

  def writeFmt(self, fmt, *a):
    return self.write(struct.pack(fmt, *a))

  def read_all(self):
    p = self.tell()
    self.seek(0)
    v = self.read()
    self.seek(p)
    return v

  def dump(self):
    return self.getvalue()

  def get_len(self):
    org = self.tell()
    self.seek(0, os.SEEK_END)
    end = self.tell()
    self.seek(org)
    return end

  def get_pos(self):
    return self.tell()

  def available(self):
    return self.get_len() - self.get_pos()

  def hex_dump(self, in_row=16, group_by=1, title=None, head=True):
    n_groups = in_row / group_by
    n_left = in_row % group_by
    hex_size = ((2 * group_by) + 1) * n_groups + 2 * n_left + 1
    asc_size = in_row
    row_fmt = "| {0:10s} : {1:" + str(asc_size) + "} : {2:" + str(hex_size) + "}\n"

    def fmt_row(xa, xb, xc):
      return row_fmt.format(xa, xb, xc)

    def offset(a):
      return "{0:#010x}".format(a)

    S = '\n'
    if head:
      if title:
        S += " .----[ {0} ]----- \n".format(title)
      S += fmt_row("+ Offset", "ASCII", "HEX")
    p = self.tell()  # save
    self.seek(0)  # rewind
    while True:
      off = self.tell()
      chunk = self.read(in_row)
      str_hex = ''
      str_asc = ''
      hex_chunk = ''
      for c in map(ord, chunk):
        str_asc += chr(c) if 32 <= c < 127 else '.'
        hex_chunk = "{0:02x}".format(c) + hex_chunk
        if len(hex_chunk) == group_by * 2:
          str_hex += hex_chunk + ' '
          hex_chunk = ''
      if len(hex_chunk) != 0:
        str_hex += hex_chunk + ' '
      S += fmt_row(offset(off), str_asc, str_hex)
      if len(chunk) < in_row:
        break
    S += fmt_row(offset(self.tell()), "", "")
    S += "`-- \n"
    self.seek(p)
    return S





