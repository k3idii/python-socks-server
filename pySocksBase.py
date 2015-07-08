""" Mother of 4 & 5 classes """

import socket
import select

import logging 

import re

BLOCK_SIZE = 4096

LOCASE = re.compile("[a-z]+")

SIDE_LOCAL = "LOCAL"
SIDE_REMOTE = "REMOTE"


class socksException(Exception):
  """ socs exception """
  pass


class basicTcpForwarder(object): # hackable 

  def __init__(self, local_socket, remote_socket, options=dict()):
    self.l_sock = local_socket
    self.r_sock = remote_socket
    self.options = options 
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
      events = queue.poll( timeout )
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
            logging.info( 'Endpoint [ {} ] chunk is none, terminating ... '.format(name) )
            keep_working = False
            break
          chunk = self.process_chunk(name, chunk)
          if chunk: # process_chunk can return None ... handle this here :
            logging.debug('Data from {} -> {}'.format(A['name'],B['name']))
            B['sock'].send(chunk)
          else:
            logging.debug('No chunk ...')
        else:
          logging.debug("UNKNOW EVENT")
      if not there_was_event:
        self.idle_loop()
  
    for k,v in self.endpoints.iteritems():
      v['sock'].close()
    

 


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

  def newUdpListener(self, host=None, port=None):
    """ create new listening udp socket, for udp-over-socks """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind((host, port))
    return sock

  def resolveHostname(self, host):
    """ use to resolve hostname """
    logging.debug("Resolving [%s]" % (host))
    return socket.gethostbyname(host)

  def isHostname(self, addr):
    """ check if address is hostname """
    if ":" in addr:
      logging.debug("[%s] is IPv6 !" % (addr))
      return False
    elif LOCASE.search(addr.lower()) is None:
      logging.debug("[%s] is IPv4" % (addr))
      return False
    else:
      logging.debug("[%s] is hostname" % (addr))
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

  def connectTo(self, tgt):
    """ establish connection to host|port """
    try:
      host, port = tgt
      if self.isHostname(host): 
        logging.debug('target is not ip, resolving ...')
        tmp = self.resolveHostname(host)
        if tmp is None:
          logging.error("Fail to resolve [%s]" % (host))
          return None
        logging.debug("[%s] resolved to [%s]" % (host,tmp))
        host = tmp
        tgt = (host, port)
      else:
        logging.debug("target [%s] is IP address, not resolving" % (host))
      tgt = self.check_target(tgt)
      logging.debug("socket->new")
      sock = self.make_socket()
      logging.debug("socket->connect")
      self.socket_connect( sock, tgt )
    except socket.error as sock_e:
      logging.error("[connect-to] Socket-level error: %s!" % (`sock_e`))
      return None
    except socket.timeout as sock_e:
      logging.error("[connect-to] Socket timeout ")
      return None
    except Exception as ex:
      logging.error('[connect-to] Unknown error : {}'.format(`ex`))
      raise
    logging.debug("Connected !")
    return sock

  def tcp_forward(self, local_socket, remote_socket ):
    dev = basicTcpForwarder( local_socket=local_socket, remote_socket=remote_socket )
    dev.run()


# vim: set expandtab ts=2 sw=2:
