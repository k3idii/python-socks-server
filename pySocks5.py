""" socks 5 """

import struct
import logging 
import pySocksBase
from misc.binBuffer import extStringIO


SOCKS5_CMD_CONNECT = 1
SOCKS5_CMD_BIND = 2
SOCKS5_CMD_UDP = 3

SOCKS5_METHOD_NONE = 0x00
SOCKS5_METHOD_GSSAPI = 0x01
SOCKS5_METHOD_USERPASS = 0x02
SOCKS5_METHOD_FAIL = 0xFF

SOCKS5_ADDR_IP4    = 1
SOCKS5_ADDR_IP6    = 4
SOCKS5_ADDR_DOMAIN = 3

SOCKS5_RESP_SUCCESS     = 0x00
SOCKS5_RESP_FAIL        = 0x01
SOCKS5_RESP_NOTALLOWED  = 0x02
SOCKS5_RESP_NETUNREACH  = 0x03
SOCKS5_RESP_HOSTUNREACH = 0x04
SOCKS5_RESP_REFUSED     = 0x05
SOCKS5_RESP_TTLEXP      = 0x06
SOCKS5_RESP_CMDNOSUPP   = 0x07
SOCKS5_RESP_ADDRNOSUPP  = 0x08


class socksServer(pySocksBase.socksServer):
  """ socks v5 server class """  

  def setup(self):
    """ setup sock5 """
    logging.info(" ~~~~~ SOCKS 5 ~~~~~~ ")
    self.version = 5
    self.authData = None
    self.authPreferences = 0

  def selectAuthMethod(self, methods): # override this :)
    """ select one of provided auth methods """
    logging.debug("Select auth method ...")
    return methods[self.authPreferences] # how comples is it !? :)

  def processAuthMethod(self, mid):
    """ call aprpo. auth function """
    logging.info("Try to auth using method 0x%02X" % (mid))
    funcName = "auth_%02x" % (mid) 
    logging.debug("> Try to call %s" % (funcName))
    fn = getattr(self, funcName, None)
    if fn and callable(fn):
      try:
        return fn()
      except Exception as err:
        raise pySocksBase.socksException("Fail to run auth method, reason: %s" % (`err`))
    else:
      raise pySocksBase.socksException("authmethod [%s] not implemented !"%(funcName))
  
  def processCommand(self, cmd):
    logging.info("Proccessing command 0x%02X" % (cmd))
    funcName = "command_%02X" % (cmd)
    logging.debug("> Try to call %s" % (funcName))
    fn = getattr(self, funcName, None)
    if fn and callable(fn):
      try:
        return fn()
      except Exception as err:
        raise pySocksBase.socksException("Fail to run command, reason: %s" % (`err`))
    else:
      raise pySocksBase.socksException("Command not implemented 0x%02X" % (cmd))

  def auth_00(self):
    """ auth: none """
    logging.info("Auth method 0x00 (no auth)")
    return True

  def auth_02(self):
    """ auth: user/password """
    logging.info("Auth method 0x02 (user/password")
    #data = self.client_socket.recv(pySocksBase.BLOCK_SIZE)
    data = self.recvBlock()
    stream = extStringIO(data)
    #print stream.hexDump()
    ver, uLen = stream.readFmt("BB")
    usr = ""
    if uLen > 0:
      usr  = stream.readFmtSingle(str(uLen) + "s")
    pLen = stream.readFmtSingle("B")
    pwd = ""
    if pLen > 0:
      pwd = stream.readFmtSingle(str(pLen) + "s")
    logging.info("provided version/user/password: %s/%s/%s" % (ver, usr, pwd))
    logging.debug(" <-- here we should check suser/password ")
    self.client_socket.send(struct.pack("BB", 1, 0))
    return True

  def prepareAnswer(self, status=SOCKS5_RESP_SUCCESS, addrType=SOCKS5_ADDR_IP4, addr="0.0.0.0", port=0):
    """ prepare socks5 answer packet """
    answer = extStringIO("")
    answer.writeFmt("BBBB", self.version, status, 0, addrType)
    if addrType == SOCKS5_ADDR_IP4:
      answer.writeFmt("BBBB", *(map(int, addr.split('.'))))
    elif addrType == SOCKS5_ADDR_IP6:
      answer.write('0' * 16)
    elif addrType == SOCKS5_ADDR_DOMAIN:
      answer.writeFmt("B", len(addr))
      answer.write(addr)
    answer.writeFmt(">H", port)
    return answer.dump()

  def run(self):
    """ run service """
    #data = self.client_socket.recv(1024)
    data = self.recvBlock()
    stream = extStringIO(data)
  
    ver, nMethods = stream.readFmt("BB")
    if ver != self.version:
      raise Exception("Version mismatch [ %d != 5]"%(ver))

    methods = stream.readFmt("B"*nMethods)
    logging.info("Received available auth methodds: (n=%d) [ %s ]" % (nMethods, `methods`))

    m = self.selectAuthMethod(methods) # return 0xFF if none
    logging.debug("Selected auth method : 0x%02X" % (m))
    self.client_socket.send( struct.pack("BB", self.version, m))

    if m == SOCKS5_METHOD_FAIL:
      self.terminate()
      return

    if not self.processAuthMethod(m):
      self.terminate()
      return
    
    # not terminated? ->auth ok ;)

    #data = self.client_socket.recv(1024)
    data = self.recvBlock()
    stream = extStringIO(data)

    ver, cmd, _, addrType = stream.readFmt("BBBB")
    
    if ver != self.version:
      raise Exception("Version mismatch [%d!=5]" % (ver))

    logging.info("Client send command 0x%02X" % (cmd))

    host = None
    port = -1
    if addrType == SOCKS5_ADDR_IP4:
      binIp, port = stream.readFmt(">4sH")
      host = '.'.join(map(str, struct.unpack("BBBB", binIp)))
    elif addrType == SOCKS5_ADDR_IP6:
      binIp, port = stream.readFmt(">16sH")
      raise Exception("Implement me lol ( ipv6 <3 )")
    elif addrType == SOCKS5_ADDR_DOMAIN:
      size = stream.readFmtSingle("B")
      host = stream.readFmtSingle(str(size)+"s")
      port = int(stream.readFmtSingle(">H"))
    else:
      self.client_socket.send(self.prepareAnswer(SOCKS5_RESP_ADDRNOSUPP))
      self.terminate()
      raise Exception("Unsupported address type (%02X)" % (addrType))
      #return False <- exception, no need to return 
    logging.info(" Target host:port ( %s : %d ) " % (host, port))
    self.target = (host, port)
    if self.processCommand(cmd):
      self.terminate()
    else:
      self.client_socket.send(self.prepareAnswer(SOCKS5_RESP_CMDNOSUPP))
      self.terminate()
      logger.error("Command [%d] fail !"%cmd)

  def command_01(self):
    """ connect """
    remote_socket = self.connectTo(self.target)
    if remote_socket is None:
      logging.info("Unable to connect to [%s]" % (`self.target`))
      self.client_socket.send(self.prepareAnswer(SOCKS5_RESP_HOSTUNREACH))
      self.terminate()
      return True
    self.client_socket.send(self.prepareAnswer(SOCKS5_RESP_SUCCESS))    
    self.tcpForwardMode(self.client_socket, remote_socket)
    self.terminate()
    return True

  def command_02(self): # bind
    """ bind """
    logging.debug("SOCKD5-bind")
    logging.error("TO BE IMPLEMENTED!")
    return True

  def command_03(self): # udp
    """ udp assoc. """
    logging.debug("SOCKS5-udp request")
    listening_udp_socket = self.newUdpListener()
    # keep handling udp connections till tcp socket terminates 
    logging.error("TO BE IMPLEMENTED!")
    self.terminate()
    return True


