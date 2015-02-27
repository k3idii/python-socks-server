""" Mother of 4 & 5 classes """

import socket
import select
import logging 
import re

BLOCK_SIZE = 4096
LOCASE = re.compile("[a-z]+")


class socksException(Exception):
  """ socs exception """
  pass


class socksServer(object):
  """ x """
  def __init__(self, client_socket, client_address, meta=None):
    """ constructor """
    self.client_socket = client_socket
    self.client_address = client_address
    self.meta = meta
    logging.debug("Incoming connection from %s" % (`client_address`) )
    self.setup()
    self.run()

  def setup(self):
    """ overload this """
    pass

  def run(self):
    """ overload this """
    pass

  def terminate(self):
    """ close client connection """
    self.client_socket.close()
  
  def recvBlock(self,min_len=1):
    data = self.client_socket.recv(BLOCK_SIZE)
    if not data or len(data) < min_len:
      raise socksException("Fail to recv data from client !")
    return data

  def newUdpListener(self, host=None, port=None):
    """ create new listening udp socket, for udp-over-socks """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind((host, port))
    return sock

  def resolveHostname(self, host):
    """ resolve hostname to ip """
    logging.debug("Resolving [%s]" % (host))
    return socket.gethostbyname(host)

  def isHostname(self, addr):
    """ check if address is hostname OR ip(4|6) """
    if ":" in addr: # uber-test for ipv6 
      logging.debug("[%s] is IPv6 !" % (addr))
      return False
    elif LOCASE.search(addr.lower()) is None: # uber-test for hostname (non-ip4)
      logging.debug("[%s] is IPv4" % (addr))
      return False
    else: # 99.99% sure that this is ipv4
      logging.debug("[%s] is hostname" % (addr))
      return True 
  
  def preConnect(self, sock):
    """ for hooks """
    return sock

  def postConnect(self, sock):
    """ for hooks """
    return sock

  def connectTo(self, tgt):
    """ establish (socket) connection to host:port """
    try:
      host, port = tgt
      if self.isHostname(host): 
        tmp = self.resolveHostname(host)
        if tmp is None:
          logging.error("Fail to resolve [%s]" % (host))
          return None
        logging.debug("[%s] resolved to [%s]" % (host,tmp))
        host = tmp
        tgt = (host, port)
      else:
        logging.debug("[%s] is already IP address, not resolving" % (host))
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      logging.debug("pre-connect()")
      sock = self.preConnect(sock)
      logging.debug("socket.connect()")
      sock.connect(tgt)
      logging.debug("post-connect()")
      sock = self.postConnect(sock)
    except socket.error as sock_e:
      logging.error("[connect-to] Socket-level error: %s!" % (`sock_e`))
      return None
    except socket.timeout as sock_e:
      logging.error("[connect-to] Socket timeout ")
      return None
    logging.debug("Connected !")
    return sock

  def encapsulateData(self, data, direction):
    """ Support for data encapsulation (for hooks) """
    return data
  
  def tcpForwardMode(self, sock_i, sock_o, poolTimeout=0.1):
    """ Start TCP data forwarding """
    logging.info("Start TCP forward mode -> ")

    sock_i.setblocking(0)
    sock_o.setblocking(0)

    queue = select.poll()
    queue.register(sock_i, select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR)
    queue.register(sock_o, select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR)

    keep_working = True
    while keep_working:
      events = queue.poll(poolTimeout)
      for fd, flag in events:
        if fd == sock_i.fileno():
          logging.debug(' data : CLIENT -> REMOTE')
          if flag & select.POLLIN:
            chunk = sock_i.recv(BLOCK_SIZE)
            if not chunk:
              logging.info('Client terminated connection')
              keep_working = False
              break
            #print "CLIENT:", `chunk` # log chunks
            sock_o.send(chunk)
        elif fd == sock_o.fileno():
          logging.debug(' data : CLIENT <- REMOTE ')
          if flag & select.POLLIN:
            chunk = sock_o.recv(BLOCK_SIZE)
            if not chunk:
              logging.info('Remote terminated connection')
              keep_working = False
              break
            #print "REMOTE:", `chunk` # log cunk
            sock_i.send(chunk)
        else:
          logging.error("unknown fd after poll !?")
          raise Exception("WTF !?")

    sock_i.close()
    sock_o.close()


# vim: set expandtab ts=2 sw=2:
