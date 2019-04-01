#!/usr/bin/env python

# import signal
import sys
import os
import logging
import logging.handlers
import json

import time #for testing purposes

import socket
from optparse import OptionParser

import redis
from src import redis_tools

log = logging.getLogger("BLUSE.interface")


CHANNELS = [
        "blc00",
        "blc01",
        "blc02",
        "blc03",
        "blc04",
        "blc05",
        "blc06",
        "blc07",
        "blc08",
        "blc09",
        "blc10",
        "blc11",
        "blc12",
        "blc13",
        "blc14",
        "blc15",
        "blc16",
        "blc17",
        "blc18",
        "blc19",
        "blc20",
        "blc21",
        "blc22",
        "blc23",
        "blc24",
        "blc25",
        "blc26",
        "blc27",
        "blc28",
        "blc29",
        "blc30",
        "blc31",
        "blc32",
        "blc33",
        "blc34",
        "blc35",
        "blc36",
        "blc37",
        "blc38",
        "blc39",
        "blc40",
        "blc41",
        "blc42",
        "blc43",
        "blc44",
        "blc45",
        "blc46",
        "blc47",
        "blc48",
        "blc49",
        "blc50",
        "blc51",
        "blc52",
        "blc53",
        "blc54",
        "blc55",
        "blc56",
        "blc57",
        "blc58",
        "blc59",
        "blc60",
        "blc61",
        "blc62",
        "blc63"
    ]

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--port', dest='port', type=long,
        help='Redis port to connect to', default=6379)
    (opts, args) = parser.parse_args()

    # if not opts.port:
    #     print "MissingArgument: Port number"
    #     sys.exit(-1)

    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    # logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    log.setLevel(logging.DEBUG)
    log.info("Starting distributor")
    syslog_addr = '/dev/log' if os.path.exists('/dev/log') else '/var/run/syslog'
    handler = logging.handlers.SysLogHandler(address=syslog_addr) 
    log.addHandler(handler)

    LISTEN = redis_tools.REDIS_CHANNELS.alerts

    re = redis.StrictRedis(port=opts.port)
    ps = re.pubsub(ignore_subscribe_messages=True)
    ps.subscribe(LISTEN)
    try: 
        for message in ps.listen():
            msg_parts = message['data'].split(':')
            if len(msg_parts) != 2:
                logger.info("Not processing this message --> {}".format(message))
                continue
            msg_type = msg_parts[0]
            product_id = msg_parts[1]
            if msg_type == 'configure':
                streams = json.loads(re.get("{}:streams".format(product_id)))
                print(streams)
                # for channel in CHANNELS:
                #     re.publish(channel, "")

    except KeyboardInterrupt:
        log.info("Stopping distributor")
        sys.exit(0)
    except Exception as e:
        log.error(e)
        sys.exit(1)
