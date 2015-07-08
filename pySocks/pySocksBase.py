""" Mother of 4 & 5 classes """

import socket
import select

import logging

import re

# CONST

SOCKS_VERSION_4 = 4
SOCKS_VERSION_5 = 5


BLOCK_SIZE = 4096

LOCASE = re.compile("[a-z]+")

SIDE_LOCAL = "LOCAL"
SIDE_REMOTE = "REMOTE"

class SocksException(Exception):
  """ socs exception """
  pass


class BasicTcpForwarder(object): 
  """ hackable tcp forwarcer """

  def __init__(self, local_socket, remote_socket, options=None):
    """ takes two sockets ... """
    self.l_sock = local_socket
    self.r_sock = remote_socket
    self.options = options if options else dict()
    self.endpoints = dict()
    self.endpoints[SIDE_LOCAL] = dict( sock=self.l_sock, other=SIDE_REMOTE )
    self.endpoints[SIDE_REMOTE] = dict( sock=self.r_sock, other=SIDE_LOCAL  )
    for k in self.endpoints :
      self.endpoints[k]['fd'] = self.endpoints[k]['sock'].fileno()
    self.setup()

  def setup(self):
    pass

  def process_chunk(self,name,chunk):
    return chunk

  def idle_loop(self):
    #logging.debug("Look M'a , im iddling ... ")
    pass

  def prepare_endpoint(self,name):
    pass

  def run(self):
    timeout = self.options.get('poll_time',0.05) 
    chunk_size = self.options.get('chunk_size',4096)

    logging.info("Start TCP forward mode -> ")
    queue = select.poll()
    fds = dict() # fd to endpoint name mapping 

    for k,v in self.endpoints.iteritems():
      v['sock'].setblocking(0)
      v['name'] = k
      fds[ v['fd'] ] = k
      self.prepare_endpoint(k)
      queue.register(v['sock'], select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR)
    
    keep_working = True
    while keep_working:
      there_was_event = False
      events = queue.poll( timeout * 1000 ) # seconds !!
      for fd, flag in events:
        if fd not in fds:
          logging.error("Unknown FD error at poll !")
          raise Exception("WTF fd @ poll")
        there_was_event = True
        name = fds[ fd ]
        A = self.endpoints[ name ]
        B = self.endpoints[ A['other'] ]
        logging.debug("poll event at "+name)
        if flag & select.POLLIN:
          chunk = A['sock'].recv( chunk_size )
          if not chunk:
            logging.info("Endpoint [ {0} ] chunk is none, terminating ... ".format(name) )
            keep_working = False
            break
          chunk = self.process_chunk(name, chunk)
          if chunk: # process_chunk can return None ... handle this here :
            logging.debug("Data from {0} -> {0}".format(A['name'],B['name']))
            B['sock'].send(chunk)
          else:
            logging.debug("No chunk ...")
        else:
          logging.debug("UNKNOW EVENT")
      if not there_was_event:
        self.idle_loop()
  
    for k,v in self.endpoints.iteritems():
      v['sock'].close()
    

 


class SocksServer(object):
  """ x """
  def __init__(self, client_socket, client_address, options=None):
    """ constructor """
    self.client_socket = client_socket
    self.client_address = client_address
    self.options = options if options else dict()
    logging.debug("Incoming connection from {0:s}:{1:d}".format(*client_address))
    self.setup()
    self.run()

  def setup(self):
    """ overload this """
    pass

  def run(self):
    """ overload this """
    logging.error("I'm just prototype ... ")

  def terminate(self):
    """ close client connection """
    self.client_socket.close()

  def newUdpListener(self, host=None, port=None):
    """ create new listening udp socket, for udp-over-socks """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind((host, port))
    return sock

  def resolve_hostname(self, host):
    """ use to resolve hostname """
    logging.debug("Resolving [{0:s}]".format(host))
    return socket.gethostbyname(host)

  def isHostname(self, addr):
    """ check if address is hostname """
    if ":" in addr:
      logging.debug("[{0:s}] is IPv6 !".format(addr))
      return False
    elif LOCASE.search(addr.lower()) is None:
      logging.debug("[{0:s}] is IPv4".format(addr))
      return False
    else:
      logging.debug("[{0:s}] is hostname".format(addr))
      return True 
  
  def make_socket(self):
    """ """
    return socket.socket( socket.AF_INET, socket.SOCK_STREAM ) 

  def check_target(self, tgt):
    """ """
    return tgt

  def socket_connect(self, sock, tgt):
    """ """
    sock.connect( tgt )
    return sock

  def connect_to(self, tgt):
    """ establish connection to host|port """
    try:
      host, port = tgt
      if self.isHostname(host): 
        logging.debug("target is not ip, resolving ...")
        tmp = self.resolve_hostname(host)
        if tmp is None:
          logging.error("Fail to resolve [{0:s}]".format(host))
          return None
        logging.debug("[{0:s}] resolved to [{1:s}]".format(host, tmp))
        host = tmp
        tgt = (host, port)
      else:
        logging.debug("target [{0:s}] is IP address, not resolving".format(host))
      tgt = self.check_target(tgt)
    except Exception as ex:
      logging.error("[connect-to] Fail at pre-connect ({0:s})".format(`ex`))
      return None
    try:
      logging.debug("socket->new")
      sock = self.make_socket()
      logging.debug("socket->connect")
      self.socket_connect( sock, tgt )
    except socket.timeout :
      logging.error("[connect-to] Socket timeout ")
      return None
    except socket.error as sock_e:
      logging.error("[connect-to] Socket-level error: {0:s}!".format(`sock_e`))
      return None
    except Exception as ex:
      logging.error("[connect-to] Unknown error : {}".format(`ex`))
      raise
    logging.debug("Connected !")
    return sock

  def tcp_forward(self, local_socket, remote_socket ):
    dev = BasicTcpForwarder( local_socket=local_socket, remote_socket=remote_socket )
    dev.run()


# vim: set expandtab ts=2 sw=2:
