import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def get_logger(name: str, *, level=None, stdout=False) -> logging.Logger:
    logger = logging.getLogger(name)

    level = level or os.environ.get('LOG_LEVEL', logging.INFO)
    logger.setLevel(level)

    file_handler = RotatingFileHandler(
        os.environ.get('LOG_FILE_PATH', 'log.log'),
        maxBytes=int(os.environ.get('LOG_MAX_MBYTES', 10)) * 1_000_000,
        backupCount=int(os.environ.get('LOG_BACKUPS', 1))
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    if stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    return logger
