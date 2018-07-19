# Copyright 2016 SKA South Africa (http://ska.ac.za/)

import logging
import argparse
import tornado.gen
import uuid
from katportalclient import KATPortalClient
import redis

logger = logging.getLogger('BLUSE.interface')

SUBARRAY_NUMBER = 2
HOST = 'monctl.devnmk.camlab.kat.ac.za'
SENSORS = ['target', 'pos.request-base-ra', 'pos.request-base-dec', 'observer']

def on_update_callback(msg_dict):
    """Handler for every JSON message published over the websocket."""
    print "GOT message:"
    for key, value in msg_dict.items():
        if key == 'msg_data':
            print '\tmsg_data:'
            for data_key, data_value in msg_dict['msg_data'].items():
                print "\t\t{}: {}".format(data_key, data_value)
        else:
            print "\t{}: {}".format(key, value)

@tornado.gen.coroutine
def main():
    """ This function will do all the work. 

    It will:
        -Query redis database for subarray number info
        -Establish KATPortalClient Connections and
        subscribe to appropriate messages
        -Periodically query KATPortalClients for schedule block info
        -Publish this info to the redis database

    Args:
        None

    Returns:
        None

    Example:
        >>> io_loop = tornado.ioloop.IOLoop.current()
        >>> io_loop.run_sync(main)
    """

    # Here is an example of requesting schedule block info:
    # Change URL to point to a valid portal node.  Subarray can be 1 to 4.
    # Note: if on_update_callback is set to None, then we cannot use the
    #       KATPortalClient.connect() method (i.e. no websocket access).
    portal_client = KATPortalClient('http://{}/api/client/{}'.
                                    format(HOST, SUBARRAY_NUMBER),
                                    on_update_callback=on_update_callback, 
                                    logger=logger)

    # First connect to the websocket, before subscribing.
    yield portal_client.connect()

    # Use a namespace with a unique name when subscribing to avoid a
    # clash with existing namespaces.
    namespace = 'namespace_' + str(uuid.uuid4())

    # Subscribe to the namespace (async call) - no messages will be received yet,
    # as this is a new namespace.
    result = yield portal_client.subscribe(namespace)
    print "Subscription result: {} identifier(s).".format(result)


if __name__ == '__main__':
    # Start up the tornado IO loop.
    # Only a single function to run once, so use run_sync() instead of start()
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.run_sync(main)