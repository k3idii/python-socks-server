""" basic/minimalistic socks server """
import SocketServer
import logging

from dispatcher import socks_proxy_dispatcher
import loggerSetup  # <- way cooler logger output

# Be less verbose:
# loggerSetup.stdLog.setLevel(logging.INFO)

class MyTcpHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    srv = socks_proxy_dispatcher(self.request, self.client_address, use_default=True)


class MyTcpServer(SocketServer.TCPServer):
  allow_reuse_address = True


def main():
  listen_addr = ("127.0.0.1", 9876)
  logging.info("Will listen on [{0}:{1}]".format(*listen_addr))
  srv = MyTcpServer(listen_addr, MyTcpHandler)
  srv.serve_forever()


if __name__ == '__main__':
  main()

