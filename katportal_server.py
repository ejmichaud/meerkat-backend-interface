# Copyright 2016 SKA South Africa (http://ska.ac.za/)

import logging
import argparse
import tornado.gen
from katportalclient import KATPortalClient
import redis

logger = logging.getLogger('katportalclient.example')
logger.setLevel(logging.DEBUG)


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
                                    format(args.host, args.sub_nr),
                                    on_update_callback=None, logger=logger)

    # Get the IDs of schedule blocks assigned to the subarray specified above.
    sb_ids = yield portal_client.schedule_blocks_assigned()
    print "\nSchedule block IDs on subarray {}\n{}".format(args.sub_nr, sb_ids)
    # Example output:
    #   Schedule block IDs on subarray 1:
    #   [u'20161010-0001', u'20161010-0002', u'20161010-0003']

    # Fetch the details for one of the schedule blocks found.
    if len(sb_ids) > 0:
        sb_detail = yield portal_client.schedule_block_detail(sb_ids[0])
        print "\nDetail for SB {}:\n{}\n".format(sb_ids[0], sb_detail)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Download schedule block info for a subarray and print to stdout.")
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help="hostname or IP of the portal server (default: %(default)s).")
    parser.add_argument(
        '-s', '--sub_nr',
        default='1',
        type=int,
        help="subarray number (1, 2, 3, or 4) to request schedule for "
             "(default: %(default)s).")
    parser.add_argument(
        '-v', '--verbose',
        dest='verbose', action="store_true",
        default=False,
        help="provide extremely verbose output.")
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    # Start up the tornado IO loop.
    # Only a single function to run once, so use run_sync() instead of start()
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.run_sync(main)