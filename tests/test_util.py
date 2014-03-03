# -*- coding: utf-8 -*-
from nose.tools import *
from website import util


def test_groupby():
    dictlist = [{'is_registered': True, 'id': 1},
        {'is_registered': False, 'id': 2},
        {'is_registered': True, 'id': 3}]
    result = util.groupby(dictlist, key=lambda x: x['is_registered'])
    print(result)
    assert_equal(len(result[True]), 2)
    assert_equal(len(result[False]), 1)
