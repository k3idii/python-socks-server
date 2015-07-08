""" socks 4 & 5 dispatcher """

import socket
import struct

import pySocks


def socks_proxy_dispatcher(client_socket, client_address, v4_class=None, v5_class=None, options=None,
                           use_default=False):
  """ peek one byte -> create and return socks4 or socks5 server object """

  if v4_class is None and use_default:
    v4_class = pySocks.Socks4Server
  if v5_class is None and use_default:
    v5_class = pySocks.Socks5Server

  one_byte = client_socket.recv(1, socket.MSG_PEEK)
  if not one_byte or len(one_byte) != 1:
    raise Exception("Fail to peek 1 byte !")

  version = struct.unpack("B", one_byte)[0]  # # way much cooler than just  version = ord(one_byte[0])

  if version == pySocks.SOCKS_VERSION_4 and v4_class:
    srv_class = v4_class
  elif version == pySocks.SOCKS_VERSION_5 and v5_class:
    srv_class = v5_class
  else:
    raise Exception("Unsupported version : {0:02X}".format(version))

  return srv_class(client_socket, client_address, options=options)
