import logging,logging.handlers
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

stdLog = logging.StreamHandler(stream=sys.stdout)
stdLog.setLevel(logging.DEBUG)

sysLog = logging.handlers.SysLogHandler('/dev/log')
sysLog.setLevel(logging.INFO)

stdLog.setFormatter( logging.Formatter('%(asctime)s [%(levelname)-7s]  %(message)s') )
logger.addHandler( stdLog )

#sysLog.setFormatter( logging.Formatter('%(levelname)s : %(message)s') )
#logger.addHandler( sysLog )




