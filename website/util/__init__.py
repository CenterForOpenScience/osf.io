# -*- coding: utf-8 -*-
from collections import defaultdict

from . import rubeus


def groupby(iterable, key):
    res = defaultdict(list)
    for each in iterable:
        group = key(each)
        res[group].append(each)
    return dict(res)
