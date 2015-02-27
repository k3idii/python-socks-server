""" socks 4 & 5 dispatcher """
import socket
import struct
    

def proxyDispatcher(client_socket, client_address, v4class=None, v5class=None, meta=None):
  """ peek one byte -> create socks 4 || 5 object  """
  if v4class is None:
    import pySocks4
    v4class = pySocks4.socksServer
  if v5class is None:
    import pySocks5 
    v5class = pySocks5.socksServer 
  oneByte = client_socket.recv(1, socket.MSG_PEEK)
  if not oneByte or len(oneByte) != 1:
    raise Exception("Fail to peek 1 byte !")
  version = struct.unpack("B", oneByte)[0] #  # way much cooler than ord
  if version == 4:
    c = v4class
  elif version == 5:
    c = v5class
  else:
    raise Exception("Unsupported version : %02X" % (version))
  return c(client_socket, client_address, meta=meta)


