""" advanced socks server -> custom dns resolver + multiple output routes :) """
import socket
import select
import logging 
import threading
import random

import dns.resolver
import dns.rdataclass
import dns.rdatatype 

import loggerSetup
import pySocks 

from dispatcher import socks_proxy_dispatcher



CONFIG = [
   dict(label='default', listen=('127.0.0.1',9051), bind_addr=('127.0.0.2',0), dns='127.0.0.1')
   ,
   dict(label='local2', listen=('127.0.0.1',9052), bind_addr=('127.0.0.1',0))
]

try:
  from local_config import CONFIG # import local settings
except Exception:
  logging.error("Fail to load local settings !")

POLL_TIME = 100

def resolve_host_usgin_ns(name, srv, src_addr=None, ):
  """ Try to resolve hostname using specific DNS server, bind to specific addr (if provided) """
  #TODO: implement ipv6 ...
  try: #TODO: move this try near query() statement .... 
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [srv] # multiple server support ?!
    # src_addr should be (None,string_ip)
    qtype = dns.rdatatype.A
    qclass = dns.rdataclass.IN
    answer = resolver.query(qname=name, rdtype=qtype, rdclass=qclass, source=src_addr)
    # we should be able to do : host = answer.rrset[0].address , but ...
    hosts = [] 
    for rr in answer.rrset:
      if rr.rdclass == qclass and rr.rdtype == qtype:
        hosts.append( rr.address )
    hosts_count =len(hosts)
    if hosts_count < 1:
      logging.error("DNS query did not return any useful data !")
      raise None
    logging.debug("DNS server returned {0:d} records: {1:s}".format(hosts_count, `hosts`))
    if hosts_count == 1:
      return hosts[0]
    return random.choice( hosts )
    ## del me : host = answer.rrset.items[0].address
  except Exception as err:  # nxdomain || any other error
    logging.error("DNS fail : {0:s}".format(`err`))
    return None


def bind_connect(obj, sock, tgt):
  bind_addr = obj.options.get('bind_addr',None)
  if bind_addr:
    logging.info("Bind socket to address {0:s}:{1:d}".format(*bind_addr))
    try:
      sock.bind(bind_addr)
    except socket.error:
      logging.error("FAIL to bind  to {0:s} !".format(bind_addr))
      raise
  logging.info("socket->connect({0:s}:{1:d})".format(*tgt))
  try:
    sock.connect(tgt)
  except Exception :
    logging.error("Fail to connect !")
    raise
  return sock


def try_external_resolve(obj, host):
  dns_srv = obj.options.get('dns',None)
  bind_addr = obj.options.get('bind_addr',None)
  if dns_srv:
    logging.info("Try to resolve [{0:s}] using [{1:s}] (bind-to:{2:s})".format(host, dns_srv, bind_addr))
    return resolve_host_usgin_ns(host, dns_srv, bind_addr[0])
  else:
    logging.info("No DNS server provided! Fallback to default resolve method.")
  return socket.gethostbyname(host)


pySocks.Socks5Server.resolve_hostname = try_external_resolve
pySocks.Socks4Server.resolve_hostname = try_external_resolve

pySocks.Socks5Server.socket_connect = bind_connect
pySocks.Socks4Server.socket_connect = bind_connect


def process_connection(sock, addr, opt): # run this as thread ;)
  """ Handle new connection (as thread), pass to dispatcher """
  try:
    socks_proxy_dispatcher(sock, addr, options=opt, use_default=True )
    #socks_proxy_dispatcher(sock, addr, v4_class=routing4, v5_class=routing5, options=opt)
  except Exception as e:
    logging.error("Client-error: {0:s}".format(`e`))



def main():
  """ run me ;) """
  READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
  READ_WRITE = READ_ONLY | select.POLLOUT
  queue = select.poll()
  fds = {}
  logging.info("Processing config ...")
  for opt in CONFIG:
    srv = None
    try:
      srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      logging.info("Option: {0:s}".format(`opt`))
      srv.bind(opt['listen'])
      srv.listen(5)
      opt['srv'] = srv
      opt['fd'] = srv.fileno()
      fds[opt['fd']] = opt
      logging.info("Bind to ({0}:{1}) && listening ... ".format(*opt['listen']))
      queue.register(srv, READ_ONLY)
      logging.info(" ( register FD:{0:s} ) ".format(`srv`))
    except Exception as err:
      logging.error("Fail to setup server ({0:s}) , reason: {1:s}".format(`srv`, `err`))

  keep_working = True
  while keep_working:
    try:
      events = queue.poll(POLL_TIME)
      for fd, flag in events:
        if not fd in fds:
          raise Exception("Em .. unknown FD !?")
        opt = fds[fd]
        sock, addr = opt['srv'].accept()
        thr = threading.Thread(target=process_connection, args=(sock, addr, opt))
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

