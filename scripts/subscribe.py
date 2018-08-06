"""
This script subscribes to a set of sensors upon receiving a ?configure request.
It publishes the sensor values to the redis database with formatting specified
in the ../REDIS_DOCUMENTION.md documentation.
"""

import argparse
import logging
import uuid

import tornado.gen
from katportalclient import KATPortalClient

import redis
from src.redis_tools import REDIS_CHANNELS, write_pair_redis

logger = logging.getLogger('BLUSE.interface')

def on_update_callback(msg_dict):
    """Handler for every JSON message published over the websocket."""
    value = msg_dict['msg_data']
    sensor_name = value['name']
    key = "{}:{}".format(product_id, sensor_name)
    write_pair_redis(redis_server, key, repr(value))

@tornado.gen.coroutine
def main():
    # Change URL to point to a valid portal node.
    # If you are not interested in any subarray specific information
    # (e.g. schedule blocks), then the number can be omitted, as below.
    portal_client = KATPortalClient(cam_url, on_update_callback, logger=logger)

    # First connect to the websocket, before subscribing.
    yield portal_client.connect()

    # Use a namespace with a unique name when subscribing to avoid a
    # clash with existing namespaces.
    namespace = 'namespace_' + str(uuid.uuid4())

    # Subscribe to the namespace (async call) - no messages will be received yet,
    # as this is a new namespace.
    result = yield portal_client.subscribe(namespace)
    logger.info("Subscription result: {} identifier(s).".format(result))

    # Set the sampling strategies for the sensors of interest, on our custom
    # namespace.  In this example, we are interested in a number of patterns,
    # e.g. any sensor with "target" in the name.  The response messages will
    # be published to our namespace every 10 seconds.
    result = yield portal_client.set_sampling_strategies(
        namespace, sensors,
        'period 10.0') # get sensors every 10 seconds
    logger.info("\nSet sampling strategies result: {}.\n".format(result))


if __name__ == '__main__':
    # TODO: Add sensors to subscribe to on ?configure request
    sensors = ["target", "pos_request_base_ra", "pos_request_base_dec"]
    redis_server = redis.StrictRedis()
    io_loop = tornado.ioloop.IOLoop.current()
    pub_sub = redis_server.pubsub(ignore_subscribe_messages=True)
    pub_sub.subscribe(REDIS_CHANNELS.alerts)
    for message in pub_sub.listen():
        msg_parts = message['data'].split(':')
        if len(msg_parts) == 2 and msg_parts[0] == 'configure':
            product_id = msg_parts[1]
            cam_url = redis_server.get("{}:cam:url".format(product_id))
            io_loop.add_callback(main)
            io_loop.start()
        else: # If message is NOT a configure request
            continue
