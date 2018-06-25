import signal
import threading
import time
import random
import tornado
from katcp import DeviceServer, Sensor, ProtocolFlags, AsyncReply
from katcp.kattypes import (Str, Float, Timestamp, Discrete,
                            request, return_reply)
from src.server import BLBackendInterface
# import redis

server_host = "0.0.0.0"
server_port = 5000

@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    print('Shutting down')
    yield server.stop()
    ioloop.stop()

if __name__ == "__main__":
    ioloop = tornado.ioloop.IOLoop.current()
    server = BLBackendInterface(server_host, server_port)
    server.set_concurrency_options(thread_safe=False, handler_thread=False)
    # server.set_ioloop(ioloop)
    # signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
    #    on_shutdown, ioloop, server))
    ioloop.add_callback(server.start)
    ioloop.start()