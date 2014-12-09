# encoding: utf-8

from .defaults import *

try:
    from .local import *
except ImportError:
    pass
