""" socks 5 """

import struct
import logging

import pySocksBase
from extStringIO import extStringIO

SOCKS5_CMD_CONNECT = 1
SOCKS5_CMD_BIND = 2
SOCKS5_CMD_UDP = 3

SOCKS5_METHOD_NONE = 0x00
SOCKS5_METHOD_GSSAPI = 0x01
SOCKS5_METHOD_USERPASS = 0x02
SOCKS5_METHOD_FAIL = 0xFF

SOCKS5_ADDR_IP4 = 1
SOCKS5_ADDR_IP6 = 4
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

class Socks5Exception(pySocksBase.SocksException):
  pass


class SocksServer(pySocksBase.SocksServer):
  """ socks v5 server class """
  target = None
  auth_data = None
  version = pySocksBase.SOCKS_VERSION_5
  auth_preferences = SOCKS5_METHOD_NONE

  def setup(self):
    """ setup sock5 , override me :-) """
    logging.info(" ~~~~~ SOCKS 5 SERVER ~~~~~~ ")

  def select_auth_method(self, methods): # override this :)
    """ select one of provided auth methods """
    logging.debug("Select auth method ...")
    return methods[self.auth_preferences] # how comples is it !? :)

  def process_auth_method(self, mid):
    """ call aprpo. auth function """
    logging.info("Try to auth using method {0:#02x}".format(mid))
    funcName = "auth_{0:02x}".format(mid)
    logging.debug("> Try to call {0}".format(funcName))
    fun = getattr(self, funcName, None)
    if fun and callable(fun):
      try:
        return fun()
      except Exception as err:
        raise Socks5Exception("Fail to run auth method, reason: {0}".format(`err`))
    else:
      raise Socks5Exception("authmethod [{0}] not implemented !".format(funcName))

  def process_command(self, cmd):
    logging.info("Proccessing command {0:#02x}".format(cmd))
    funcName = "command_{0:02x}".format(cmd)
    logging.debug("> Try to call {0}".format(funcName))
    fun = getattr(self, funcName, None)
    if fun and callable(fun):
      try:
        fun()
      except Exception as err:
        raise Socks5Exception("Fail to run command, reason: {0}".format(`err`))
      return True
    else:
      return False

  def auth_00(self):
    """ auth: none """
    logging.info("Auth method 0x00 (no auth)")
    return True

  def auth_02(self):
    """ auth: user/password """
    logging.info("Auth method 0x02 (user/password")
    stream = extStringIO(self.client_socket.recv(1024))
    #print stream.hexDump()
    ver, uLen = stream.readFmt('BB')
    usr = ""
    if uLen > 0:
      usr = stream.readFmt_single(str(uLen) + "s")
    pLen = stream.readFmt_single('B')
    pwd = ""
    if pLen > 0:
      pwd = stream.readFmt_single(str(pLen) + "s")
    logging.info("provided version/user/password: {0}/{0}/{0}".format(ver, usr, pwd))
    logging.debug(" <-- here we should check suser/password ")
    self.client_socket.send(struct.pack('BB', 1, 0))
    return True

  def prepare_answer(self, status=SOCKS5_RESP_SUCCESS, addrType=SOCKS5_ADDR_IP4, addr="0.0.0.0", port=0):
    """ prepare socks5 answer packet """
    answer = extStringIO("")
    answer.writeFmt('BBBB', self.version, status, 0, addrType)
    if addrType == SOCKS5_ADDR_IP4:
      answer.writeFmt('BBBB', *(map(int, addr.split('.'))))
    elif addrType == SOCKS5_ADDR_IP6:
      answer.write('0' * 16)
    elif addrType == SOCKS5_ADDR_DOMAIN:
      answer.writeFmt('B', len(addr))
      answer.write(addr)
    answer.writeFmt('>H', port)
    return answer.dump()

  def run(self):
    """ run service """
    data = self.client_socket.recv(1024)
    stream = extStringIO(data)

    ver, nMethods = stream.readFmt('BB')
    if ver != self.version:
      raise Exception("Version mismatch [ {0} != 5]".format(ver))

    methods = stream.readFmt('B' *nMethods)
    logging.info("Received available auth methodds: (n={0}) [ {1} ]".format(nMethods, `methods`))

    m = self.select_auth_method(methods) # return 0xFF if none
    logging.debug("Selected auth method : {0:#02x}".format(m))
    self.client_socket.send(struct.pack('BB', self.version, m))

    if m == SOCKS5_METHOD_FAIL:
      self.terminate()
      return

    if not self.process_auth_method(m):
      self.terminate()
      return

    # not terminated? ->auth ok ;)

    data = self.client_socket.recv(1024)
    stream = extStringIO(data)

    ver, cmd, _, addrType = stream.readFmt('BBBB')

    if ver != self.version:
      raise Exception("Version mismatch [{0:d} != {1:d}]".format(ver, self.version))

    logging.info("Client send command {0:#02x}".format(cmd))

    host = None
    port = -1
    if addrType == SOCKS5_ADDR_IP4:
      binIp, port = stream.readFmt('>4sH')
      host = '.'.join(map(str, struct.unpack('BBBB', binIp)))
    elif addrType == SOCKS5_ADDR_IP6:
      binIp, port = stream.readFmt('>16sH')
      raise Exception("Implement me lol ( ipv6 <3 )")
    elif addrType == SOCKS5_ADDR_DOMAIN:
      size = stream.readFmt_single('B')
      host = stream.readFmt_single(str(size)+ 's')
      port = int(stream.readFmt_single('>H'))
    else:
      self.client_socket.send(self.prepare_answer(SOCKS5_RESP_ADDRNOSUPP))
      self.terminate()
      raise Exception("Unsupported address type ({0:#02x})".format(addrType))
      #return False
    logging.info(" Target host:port ( {0} : {1:d} ) ".format(host, port))
    self.target = (host, port)
    if self.process_command(cmd):
      self.terminate()
      return True
    else: # command not implemented !
      self.client_socket.send(self.prepare_answer(SOCKS5_RESP_CMDNOSUPP))
      self.terminate()
      raise Socks5Exception("Command not implemented [{0:d}]".format(cmd))
      #return False

  def command_01(self):
    """ connect """
    remote_socket = self.connect_to(self.target)
    if remote_socket is None:
      logging.info("Unable to connect to [{0}]".format(`self.target`))
      self.client_socket.send(self.prepare_answer(SOCKS5_RESP_HOSTUNREACH))
      self.terminate()
      return
    self.client_socket.send(self.prepare_answer(SOCKS5_RESP_SUCCESS))
    self.tcp_forward(self.client_socket, remote_socket)
    self.terminate()

  def command_02(self): # bind
    """ bind """
    logging.debug("SOCKD5-bind")
    logging.error("TO BE IMPLEMENTED!")

  def command_03(self): # udp
    """ udp assoc. """
    logging.debug("SOCKS5-udp request")
    listening_udp_socket = self.newUdpListener()
    # keep handling udp connections till tcp socket terminates
    logging.error("TO BE IMPLEMENTED!")
    self.terminate()


