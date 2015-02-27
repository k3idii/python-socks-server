""" basic socks server """
import socket 
import traceback 
import sys

from pySocks4 import socksServer as s4srv
from pySocks5 import socksServer as s5srv

from pySocksBase import socksException

from dispatcher import proxyDispatcher 

import logging
import misc.loggerSetup

HOST = '127.0.0.1'
PORT = 9051

if len(sys.argv)>2:
  PORT = int(sys.argv[2])

if len(sys.argv)>1:
  HOST = sys.argv[1]

def main():
  """ run me ;) """
  srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  logging.info("Socket () OK")

  srv.bind((HOST, PORT))
  logging.info("Bind to (%s) OK" % (`(HOST, PORT)`))

  srv.listen(1)
  logging.info(" Listening ... ")

  try:
    while True:
      conn, addr = srv.accept()
      logging.info('>> Client connection from :'+`addr`)
      try:    
        proxyDispatcher(conn, addr, v4class=s4srv, v5class=s5srv)
      except socksException as ex:
        logging.error("[!] Socks Exception : %s" % (ex))
        logging.info(''.join(traceback.format_exception(*sys.exc_info())))
      except Exception as ex:
        logging.error("[!] Unsuported exception : %s" % (ex))
        logging.info(''.join(traceback.format_exception(*sys.exc_info())))
      conn.close()
  except KeyboardInterrupt :
    logging.error("< CTRL C ")
  except Exception as ex:
    logging.error("< FSCK : "+`ex`)

  logging.info("< Cya ! >")

main()

