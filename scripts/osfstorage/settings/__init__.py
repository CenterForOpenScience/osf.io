#!/usr/bin/env python
# encoding: utf-8

from .defaults import *


try:
    from .local import *
except ImportError as error:
    pass
