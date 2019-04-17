#!/usr/bin/env python

import signal
import sys

from meerkat_backend_interface.katportal_server import BLKATPortalClient
from meerkat_backend_interface.logger import log, set_logger


def on_shutdown():
    # TODO: uncomment when you deploy
    # notify_slack("KATPortal module at MeerKAT has halted. Might want to check that!")
    log.info("Shutting Down Katportal Clients")
    sys.exit()


def main():
    log = set_logger()
    log.info("Starting Katportal Client")

    client = BLKATPortalClient()
    signal.signal(signal.SIGINT, lambda sig, frame: on_shutdown())
    client.start()


if __name__ == '__main__':
    main()
