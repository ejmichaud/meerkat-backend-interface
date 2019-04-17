#!/usr/bin/env python

from argparse import (
    ArgumentParser,
    ArgumentDefaultsHelpFormatter)
import logging
import signal
import sys
import tornado

from meerkat_backend_interface.katcp_server import BLBackendInterface
from meerkat_backend_interface.logger import set_logger


def cli(prog=sys.argv[0]):
    usage = "{} [options]".format(prog)
    description = 'start BLUSE KATCP server'

    parser = ArgumentParser(usage=usage,
                            description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--ip',
        type=str,
        default="localhost",
        help='fixed IP of localhost system')
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=5000,
        help='port number to bind to')
    parser.add_argument(
        '--nodeset',
        dest='nodeset',
        type=str,
        default="effelsberg",
        help='name of the nodeset to use')

    # Options for development and testing
    title = "development and testing"
    description = "additional convenience settings"
    group = parser.add_argument_group(title=title,
                                      description=description)
    group.add_argument(
        '--debug',
        action='store_true',
        help='verbose logger output for debugging')

    args = parser.parse_args()
    main(ip=args.ip, port=args.port, debug=args.debug)


@tornado.gen.coroutine
def on_shutdown(ioloop, server, log):
    log.info("Shutting down server")
    yield server.stop()
    ioloop.stop()


def main(ip, port, debug):
    if debug:
        # note: debug logging will only go to logfile
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    log = set_logger(log_level=log_level)
    log.info("Starting BLBackendInterface instance")

    ioloop = tornado.ioloop.IOLoop.current()
    server = BLBackendInterface(ip, port)
    signal.signal(signal.SIGINT,
                  lambda sig, frame: ioloop.add_callback_from_signal(
                      on_shutdown, ioloop, server, log))

    def start():
        server.start()
        log.info("Listening at {0}, Ctrl-C to terminate server".format(server.bind_address))

    ioloop.add_callback(start)
    ioloop.start()


if __name__ == "__main__":
    cli()
