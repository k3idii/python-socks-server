""" socks 4 """

import struct
import logging 

import pySocksBase
from pySocksBase import socksException

from misc.binBuffer import extStringIO

SOCKS4_CMD_CONNECT = 1


RESPONSE_CODE_GRANTED = 90
RESPONSE_CODE_REJECTED = 91
RESPONSE_CODE_CONERR = 92
RESPONSE_CODE_USRERR = 92

class socksServer(pySocksBase.socksServer):
  """ socks4 server class """

  version = 4
  cmd = -1
  target = ("", 0)
  user = ""

  def setup(self):
    """ setup """
    pass

  def prepareServerReply(self, status, port=0, host="0.0.0.0"):
    """ prepare socks4 reply """
    packedIp = struct.pack("BBBB", *map(int, host.split(".")))
    return struct.pack(">BBH", 0, status, port) + packedIp

  def verifyAccess(self):
    """ verify access to socks """
    logging.info("Auth as : %s" % (self.user))
    return True

  def run(self):
    """ run service """
    data = self.client_socket.recv(1024)
    if not data:
      raise socksException("Fail to read from client !")

    stream = extStringIO(data)
    ver, cmd, port, binIp = stream.readFmt(">BBH4s")

    self.cmd = cmd
    if ver != self.version:
      raise socksException("Version mismatch : [ %d != 4 ]"%(ver))

    logging.info(" >> Got request [ ver:%d, cmd:0x%02X, port:%d ]" % (ver, cmd, port))

    numIp = struct.unpack(">i", binIp)[0]
    strIp = '.'.join(map(str, struct.unpack("BBBB", binIp)))
    if 1==1:
      print
      print "+----+----+-------+-----------------+"
      print "| VN | CM | port  |     dst.ip.addr |"
      print "+----+----+-------+-----------------+"
      print "| %02X | %02X | %05d | %s |" % (ver, cmd, port, strIp.rjust(15))
      print "+----+----+-------+-----------------+"
      print

    userData = stream.readRest()
    user, extra = userData.split('\x00', 1)

    logging.info("  Provided user: [%s] " % (user))
    self.user = user

    if numIp < 257:
      if extra[-1] != '\x00':
        raise socksException("Additional (hostname) data should be Null-term ! (is:%s"%(`data[:-1]`))
      host = extra[:-1]
      logging.info("** SOCKS-4a")
    else:
      host = strIp
      logging.info("** SOCKS-4")
      if len(extra) > 0:
        logging.info("WARNING: extra data : %s" % (`extra`))

    self.target = (host, port)
    logging.info(">> Target-host : %s" %(`self.target`))
  
    
    if not self.verifyAccess():
      logging.info(" !! client rejected !!")
      reply = self.prepareServerReply(RESPONSE_CODE_REJECTED)
      self.client_socket.send(reply)
      self.terminate()
      return
    #else:
    reply = self.prepareServerReply(RESPONSE_CODE_GRANTED)
    self.client_socket.send(reply) 

    if self.cmd == SOCKS4_CMD_CONNECT:
      remote_socket = self.connectTo(self.target)
      if remote_socket is None:
        reply = self.prepareServerReply(RESPONSE_CODE_CONERR)
        self.client_socket.send(reply)
        self.terminate()
        logging.info("!! Fail to connect to target !!")
        return
      self.tcp_forward(self.client_socket, remote_socket)
      self.terminate()


# vim: set expandtab ts=2 sw=2:$
#
