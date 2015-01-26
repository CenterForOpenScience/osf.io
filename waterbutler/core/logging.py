import re
import logging


class MaskFormatter(logging.Formatter):

    def __init__(self, fmt=None, datefmt=None, style='%', pattern=None, mask='***'):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt, style=style)
        self.pattern = re.compile(pattern)
        self.mask = mask

    def format(self, record):
        result = super().format(record)
        return self.pattern.sub(self.mask, result)
