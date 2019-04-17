import logging


def get_logger():
    """Get the logger."""
    return logging.getLogger("BLUSE.interface")


log = get_logger()


def set_logger(log_level=logging.DEBUG):
    """Set up logging."""
    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logging.basicConfig(format=FORMAT)
    log = get_logger()
    log.setLevel(log_level)

    return log
