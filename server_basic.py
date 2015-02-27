""" basic/minimalistic socks server """
import SocketServer
from dispatcher import proxyDispatcher 
import misc.loggerSetup

listen_addr = ('127.0.0.1',9051)

#Be less verbose:
#import logging
#misc.loggerSetup.stdLog.setLevel(logging.INFO)

class MyTCPHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    proxyDispatcher(self.request,self.client_address)

def main():
  """ run me ;) """
  srv = SocketServer.TCPServer(listen_addr, MyTCPHandler)
  print "Listen on: %s" % (`listen_addr`)
  srv.serve_forever()

#if __main__:
main()

