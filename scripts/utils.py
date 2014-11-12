# -*- coding: utf-8 -*-

import os
import logging
import datetime

from website import settings


def format_now():
    return datetime.datetime.now().isoformat()


def add_file_logger(logger, script_name):
    _, name = os.path.split(script_name)
    file_handler = logging.FileHandler(
        os.path.join(
            settings.LOG_PATH,
            '.'.join([name, format_now(), 'log'])
        )
    )
    logger.addHandler(file_handler)
