""" basic socks server """
import socket
import select

from pySocks4 import socksServer as s4srv
from pySocks5 import socksServer as s5srv

from pySocksBase import socksException, socksServer
from dispatcher import proxyDispatcher

import dns.resolver
import dns.rdataclass
import dns.rdatatype 
import threading
import random
#import re

import logging 
import misc.loggerSetup

CONFIG = [ dict(label="default", listen=("127.0.0.1",9051), bind_addr="127.0.0.2", xdns="127.0.0.1" )  ]

try:
  from local_config import CONFIG # import local settings
except:
  logging.error("Fail to load local settings !")

POLL_TIME = 100

def resolve_host_usgin_ns(name, srv, bind_addr=None, ):
  """ Try to resolve hostname using specific DNS server, bind to specific addr (if provided) """
  #TODO: implement ipv6 (
  try: #TODO: move this try near query() statement .... 
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [srv] # multiple server support ?!
    # bind_addr should be (None,string_ip)
    qtype = dns.rdatatype.A
    qclass = dns.rdataclass.IN
    answer = resolver.query(qname=name, rdtype=qtype, rdclass=qclass, source=bind_addr)
    host = None
    # we should be able to do : host = answer.rrset[0].address , but ...
    hosts = [] 
    for rr in answer.rrset:
      if rr.rdclass == qclass and rr.rdtype == qtype:
        hosts.append( rr.address )
    hosts_count =len(hosts)
    if hosts_count < 1:
      logging.error("DNS query did not return any usefull data !")
      raise None
    logging.debug("DNS server returned %d records: %s" % (hosts_count,`hosts`))
    if hosts_count == 1:
      host = hosts[0]
    else:
      host = random.choice( hosts )
    ## del me : host = answer.rrset.items[0].address
    return host
  except Exception as err:  # nxdomain || any other error
    logging.error("DNS fail : %s" % (`err`))
    return None

def bind_before_connect(obj,sock):
  bind_addr = obj.meta.get("bind_addr",None)
  if bind_addr:
    logging.info("Bind socket to address : %s" % (bind_addr))
    try:
      sock.bind((bind_addr, 0))
    except socket.error as sock_e:
      logging.error("FAIL to bind  to %s !" % (bind_addr))
      raise sock_e
  return sock

def try_external_resolve(obj, host):
  dns = obj.meta.get('dns',None)
  bind_addr = obj.meta.get("bind_addr",None)
  if dns: 
    logging.info("Try to resovle [%s] using [%s] (bind-to:%s)" % (host,dns,bind_addr))
    return resolve_host_usgin_ns(host, dns, bind_addr)
  else:
    logging.info("No DNS server provided! Fallback to default resolve method.")
  return socket.gethostbyname(host)



class routing4(s4srv):
  """ custom resovler + bind on connect """
  def resolveHostname(self, host):
    return try_external_resolve(self, host)

  def preConnect(self, sock):
    return bind_before_connect(self,sock)


class routing5(s5srv):
  """ custom resolver + bind on connect """
  def resolveHostname(self, host):
    return try_external_resolve(self, host)

  def preConnect(self, sock):
    return bind_before_connect(self,sock)



def processConnection(sock, addr, opt): # run this as thread ;)
  """ Handle new connection (as thread), pass to dispatcher """
  try:
    proxyDispatcher(sock, addr, v4class=routing4, v5class=routing5, meta=opt)
  except Exception as e:
    logging.error("Client-error: %s" % (`e`))

def main():
  """ run me ;) """
  READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
  READ_WRITE = READ_ONLY | select.POLLOUT
  queue = select.poll()
  fds = {}
  logging.info("Processing config ...")
  for opt in CONFIG:
    try:
      srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      logging.info("Opttion: %s" % (`opt`))
      srv.bind(opt['listen'])
      srv.listen(5)
      opt['srv'] = srv
      opt['fd'] = srv.fileno()
      fds[opt['fd']] = opt
      logging.info("Bind to (%s) && listening ... " % (`opt['listen']`))
      queue.register(srv, READ_ONLY)
      logging.info(" ( register FD:%s ) " % (`srv`))
    except Exception as err:
      logging.error("Fail to setup server (%s) , reason: %s" % (`srv`, `err`) )   

  keep_working = True
  while keep_working:
    try:
      events = queue.poll(POLL_TIME)
      for fd, flag in events:
        if not fd in fds:
          raise Exception("Em .. unknown FD !?")
        opt = fds[fd]
        sock, addr = opt['srv'].accept()
        thr = threading.Thread(target=processConnection, args=(sock, addr, opt))
        thr.start()
    except Exception as e:
      logging.error("Exception during listen() loop : ",`e`)
      logging.error("Keep going ...")
    except KeyboardInterrupt:
      keep_working = False
      logging.error("BREAK by KeyboardInterrupt")
      break
  logging.info("< Cya ! >")


#if __main__
main()

