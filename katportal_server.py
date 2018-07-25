# Copyright 2016 SKA South Africa (http://ska.ac.za/)

import logging
import argparse
import tornado.gen
import uuid
from katportalclient import KATPortalClient
import redis
from src.redis_tools import REDIS_CHANNELS

logger = logging.getLogger('BLUSE.interface')

class BLKATPortalClient(object):
    """Our client server to the Katportal

    Examples:
        >>> client = BLKATPortalClient()
        >>> client.start()

    Yes, it's that simple.

    Once initialized, the client creates a Tornado ioloop and
    a connection to the local Redis server. 

    When start() is called, a loop starts that subscribes to the 'alerts'
    channel of the Redis server. Depending on the message received, various
    processes are run (asynchronously?). This include:
        1. Creating a new KATPortalClient object specific to the
            product id we just received in a ?configure request
        2. Querying for target information when ?capture-init is 
            received and publishing this to Redis
        3. Querying for more information when ?capture-start is
            received and publishing this to Redis
        4. Deleting the corresponding KATPortalClient object once
            a ?capture-done request is sent.

    TODO:
        1. add io_loop usage on main function calls
        2. 
    """

    MSG_TO_FUNCTION = {
        'configure'     = self._configure,
        'capture-init'  = self._capture_init,
        'capture-start' = self._capture_start,
        'capture-stop'  = self._capture_stop,
        'capture-done'  = self._capture_done,
        'deconfigure'   = self._deconfigure
    }

    def __init__(self):
        """Our client server to the Katportal"""
        self.redis_server = redis.StrictRedis()
        self.p = self.redis_server.pubsub(ignore_subscribe_messages=True)
        self.io_loop = io_loop = tornado.ioloop.IOLoop.current()
        self.subarray_katportals = dict() # indexed by product id's

    def start(self):
        @tornado.gen.coroutine
        def main():
            self.p.subscribe(REDIS_CHANNELS.alerts)
            for message in self.p.listen():
                msg_parts = message.split(':')
                msg_type = msg_parts[0]
                MSG_TO_FUNCTION[msg_type](message)
        self.io_loop.add_callback(main)
        self.io_loop.start()

    def _configure(self, message):
        """Responds to configure request

        Args:
            message (str): the message sent over the alerts redis channel

        Returns:
            None, but does many things!

        Examples:
            TODO
        """
        msg_parts = message.split(':')
        product_id = msg_parts[1] # the element after the configure identifier
        cam_url = self.redis_server.get("{}:{}".format(product_id, 'cam:url'))
        client = KATPortalClient(cam_url, logger=logger)
        self.subarray_katportals[product_id] = client
        # TODO - get information?

    def _capture_init(self, message):
        """Responds to capture-init request

        Args:
            message (str): the message sent over the alerts redis channel

        Returns:
            None, but does many things!

        Examples:
            TODO
        """
        msg_parts = message.split(':')
        product_id = msg_parts[1] # the element after the capture-init identifier
        client = self.subarray_katportals[product_id]
        # TODO - get information using the client!

    def _capture_start(self, message):
        """Responds to capture-start request

        Args:
            message (str): the message sent over the alerts redis channel

        Returns:
            None, but does many things!

        Examples:
            TODO
        """
        msg_parts = message.split(':')
        product_id = msg_parts[1] # the element after the capture-start identifier
        client = self.subarray_katportals[product_id]
        # TODO - get information using the client!

    def _capture_stop(self, message):
        """Responds to capture-stop request

        Args:
            message (str): the message sent over the alerts redis channel

        Returns:
            None, but does many things!

        Examples:
            TODO
        """
        msg_parts = message.split(':')
        product_id = msg_parts[1] # the element after the capture-stop identifier
        client = self.subarray_katportals[product_id]
        # TODO - get information using the client!

    def _capture_done(self, message):
        """Responds to capture-done request

        Args:
            message (str): the message sent over the alerts redis channel

        Returns:
            None, but does many things!

        Examples:
            TODO
        """
        msg_parts = message.split(':')
        product_id = msg_parts[1] # the element after the capture-done identifier
        client = self.subarray_katportals[product_id]
        # TODO - get information using the client!

    def _deconfigure(self, message):
        """Responds to deconfigure request

        Args:
            message (str): the message sent over the alerts redis channel

        Returns:
            None, but does many things!

        Examples:
            TODO
        """
        msg_parts = message.split(':')
        product_id = msg_parts[1] # the element after the deconfigure identifier
        if product_id not in self.subarray_katportals:
            logger.WARNING("Failed to deconfigure a non-existent product_id: {}".format(product_id))
        else:
            self.subarray_katportals.pop(product_id)
            logger.INFO("Deleted KATPortalClient instance for product_id: {}".format(product_id))


if __name__ == '__main__':
    client = BLKATPortalClient()
    client.start()





#############################################################
#                   Other / Scratch Work
#############################################################

SUBARRAY_NUMBER = 2
HOST = 'monctl.devnmk.camlab.kat.ac.za'
# SENSORS = ['target', 'pos.request-base-ra', 'pos.request-base-dec', 'observer']
SENSORS = ['target']

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

#     portal_client = KATPortalClient('http://{}/api/client/'.
#                                     format(HOST),
#                                     on_update_callback=on_update_callback, 
#                                     logger=logger)
 
    # First connect to the websocket, before subscribing.
    yield portal_client.connect()

    # Use a namespace with a unique name when subscribing to avoid a
    # clash with existing namespaces.
    namespace = 'namespace_' + str(uuid.uuid4())

    # Subscribe to the namespace (async call) - no messages will be received yet,
    # as this is a new namespace.
    result = yield portal_client.subscribe(namespace)
    print "Subscription result: {} identifier(s).".format(result)

    # Set the sampling strategies for the sensors of interest, on our custom
    # namespace.  In this example, we are interested in a number of patterns,
    # e.g. any sensor with "mode" in the name.  The response messages will
    # be published to our namespace every 5 seconds.
    result = yield portal_client.set_sampling_strategies(
        namespace, SENSORS,
        'period 60.0')
    print "\nSet sampling strategies result: {}.\n".format(result)
