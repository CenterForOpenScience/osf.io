# -*- coding: utf-8 -*-

import os
import logging
import sys

from django.utils import timezone

from website import settings


def format_now():
    return timezone.now().isoformat()


def add_file_logger(logger, script_name, suffix=None):
    _, name = os.path.split(script_name)
    name = name.rstrip('c')
    if suffix is not None:
        name = '{0}-{1}'.format(name, suffix)
    file_handler = logging.FileHandler(
        os.path.join(
            settings.LOG_PATH,
            '.'.join([name, format_now(), 'log'])
        )
    )
    logger.addHandler(file_handler)


class Progress(object):
    def __init__(self, bar_len=50):
        self.bar_len = bar_len

    def start(self, total, prefix):
        self.total = total
        self.count = 0
        self.prefix = prefix

    def increment(self, inc=1):
        self.count += inc
        filled_len = int(round(self.bar_len * self.count / float(self.total)))
        percents = round(100.0 * self.count / float(self.total), 1)
        bar = '=' * filled_len + '-' * (self.bar_len - filled_len)
        sys.stdout.flush()
        sys.stdout.write('{}[{}] {}{} ... {}\r'.format(self.prefix, bar, percents, '%', str(self.total)))

    def stop(self):
        # To preserve line, there is probably a better way to do this
        print('')
