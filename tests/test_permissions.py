# -*- coding: utf-8 -*-
"""Tests for the permissions module."""
import unittest
from nose.tools import *  # PEP8 asserts

from osf.utils import permissions


def test_reduce_permissions():
    result = permissions.reduce_permissions(['read_node', 'write_node', 'admin_node'])
    assert_equal(result, 'admin')

    result2 = permissions.reduce_permissions(['read_node', 'write_node'])
    assert_equal(result2, 'write')

    result3 = permissions.reduce_permissions(['read_node'])
    assert_equal(result3, 'read')

    result = permissions.reduce_permissions(['read', 'write', 'admin'])
    assert_equal(result, 'admin')

    result2 = permissions.reduce_permissions(['read', 'write'])
    assert_equal(result2, 'write')

    result3 = permissions.reduce_permissions(['read'])
    assert_equal(result3, 'read')


def test_reduce_permissions_with_empty_list_raises_error():
    with assert_raises(ValueError):
        permissions.reduce_permissions([])


def test_reduce_permissions_with_unknown_permission_raises_error():
    with assert_raises(ValueError):
        permissions.reduce_permissions(['unknownpermission'])


def test_default_contributor_permissions():
    assert_equal(permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
        'write')


if __name__ == '__main__':
    unittest.main()
