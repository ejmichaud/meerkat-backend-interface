import signal
import os
import logging
import tornado
from src.katportal_server import BLKATPortalClient

log = logging.getLogger("BLUSE.interface")

@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    log.info("Shutting Down Katportal Clients")
    yield server.stop()
    ioloop.stop()

if __name__ == '__main__':
    
    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    # logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    log.setLevel(logging.DEBUG)
    log.info("Starting Katportal Client")
    syslog_addr = '/dev/log' if os.path.exists('/dev/log') else '/var/run/syslog'
    handler = logging.handlers.SysLogHandler(address=syslog_addr) 
    log.addHandler(handler)

    client = BLKATPortalClient()
    signal.signal(signal.SIGINT, lambda sig, frame: client.io_loop.add_callback_from_signal(client.stop))
    client.start()