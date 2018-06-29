import signal
import sys
import tornado
import logging
import json
import socket
from optparse import OptionParser
from src.server import BLBackendInterface
# from src.effelsberg.config import get_nodes
import redis

log = logging.getLogger("reynard.ubi_server")

@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    log.info("Shutting down server")
    yield server.stop()
    ioloop.stop()

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--port', dest='port', type=long,
        help='Port number to bind to', default=8888)
    parser.add_option('', '--log_level',dest='log_level',type=str,
        help='Port number of status server instance',default="INFO")
    parser.add_option('', '--nodeset',dest='nodeset',type=str,
        help='Name of the nodeset to use',default="effelsberg")
    (opts, args) = parser.parse_args()

    if not opts.port:
        print "MissingArgument: Port number"
        sys.exit(-1)


    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(opts.log_level.upper())
    log.info("Starting BLBackendInterface instance")
    ioloop = tornado.ioloop.IOLoop.current()
    server = BLBackendInterface("localhost", opts.port)
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))
    def start():
        server.start()
        log.info("Listening at {0}, Ctrl-C to terminate server".format(server.bind_address))
        # nodes = get_nodes(opts.nodeset)
        # for node in nodes:
        #     ip = socket.gethostbyname(node["host"])
        #     print node["host"],ip,node["port"]
        #     server._add_node(node["host"],ip,node["port"])
    ioloop.add_callback(start)
    ioloop.start()