# encoding: utf-8

from .defaults import *  # noqa


try:
    from .local import *
except ImportError as error:
    pass
