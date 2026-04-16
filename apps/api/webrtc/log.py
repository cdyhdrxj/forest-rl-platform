# log.py
import logging
from enum import IntEnum


class LogLevel(IntEnum):
    info = 0
    log = 1
    warn = 2
    error = 3


is_debug = True


def log(level: LogLevel, *args):
    if is_debug:
        if level == LogLevel.log:
            print(*args)
        elif level == LogLevel.info:
            logging.info(*args)
        elif level == LogLevel.warn:
            logging.warning(*args)
        elif level == LogLevel.error:
            logging.error(*args)