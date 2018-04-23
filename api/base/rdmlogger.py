# -*- coding: utf-8 -*-
# rdminfo logger
import json
import logging
import sys

class RdmLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        information = {
            "extra": {
                "kwargs": kwargs,
                "structual": True,
            }
        }
        return msg, information


class RdmLoggerFormatter:
    def __init__(self, formatter=None):
        print formatter
        self.formatter = formatter or logging.Formatter(logging.BASIC_FORMAT)


    def format(self, record):
        if not getattr(record, "structual", False):
            return self.formatter.format(record)
        d = {"msg": record.msg, "level": record.levelname}
        d.update(record.kwargs)
        return json.dumps(d)



def get_rdmlogger(name):
    alogger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(RdmLoggerFormatter())
    handler.setFormatter(formatter)
    alogger.addHandler(handler)
    alogger.setLevel(logging.INFO)
    blogger = RdmLogger(alogger, {})
    blogger.addHandler(handler)
    blogger.setLevel(logging.INFO)
    return blogger


rdmlog = logging.getLogger(__name__)
rdmlog.setLevel(logging.INFO)

formatter = RdmLoggerFormatter()

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(formatter)

rdmlog.addHandler(sh)



