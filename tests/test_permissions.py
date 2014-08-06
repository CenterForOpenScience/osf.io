# -*- coding: utf-8 -*-
"""Tests for the permissions module."""
import unittest
from nose.tools import *  # PEP8 asserts

from website.util import permissions


def test_expand_permissions():
    result = permissions.expand_permissions('admin')
    assert_equal(result, ['read', 'write', 'admin'])

    result2 = permissions.expand_permissions('write')
    assert_equal(result2, ['read', 'write'])

    result3 = permissions.expand_permissions(None)
    assert_equal(result3, [])


def test_reduce_permissions():
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
        ['read', 'write', 'admin'])


if __name__ == '__main__':
    unittest.main()
