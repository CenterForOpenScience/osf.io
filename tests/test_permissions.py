"""Tests for the permissions module."""
import unittest

import pytest

from osf.utils import permissions


def test_reduce_permissions():
    result = permissions.reduce_permissions([permissions.READ_NODE, permissions.WRITE_NODE, permissions.ADMIN_NODE])
    assert result == permissions.ADMIN

    result2 = permissions.reduce_permissions([permissions.READ_NODE, permissions.WRITE_NODE])
    assert result2 == permissions.WRITE

    result3 = permissions.reduce_permissions([permissions.READ_NODE])
    assert result3 == permissions.READ

    result = permissions.reduce_permissions([permissions.READ, permissions.WRITE, permissions.ADMIN])
    assert result == permissions.ADMIN

    result2 = permissions.reduce_permissions([permissions.READ, permissions.WRITE])
    assert result2 == permissions.WRITE

    result3 = permissions.reduce_permissions([permissions.READ])
    assert result3 == permissions.READ


def test_reduce_permissions_with_empty_list_raises_error():
    with pytest.raises(ValueError):
        permissions.reduce_permissions([])


def test_reduce_permissions_with_unknown_permission_raises_error():
    with pytest.raises(ValueError):
        permissions.reduce_permissions(['unknownpermission'])


def test_default_contributor_permissions():
    assert permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS == permissions.WRITE


if __name__ == '__main__':
    unittest.main()
