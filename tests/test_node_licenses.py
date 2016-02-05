# -*- coding: utf-8 -*-
import unittest
import functools
import json
# Python 3.x incompatible, use import builtins instead
import __builtin__ as builtins

from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.auth import Auth

from website import settings
from website.project.model import (
    NodeLog,
    NodeStateError
)
from website.project.licenses import (
    ensure_licenses,
    NodeLicense,
    serialize_node_license,
    serialize_node_license_record
)
ensure_licenses = functools.partial(ensure_licenses, warn=False)

from tests.base import OsfTestCase
from tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    NodeLicenseRecordFactory
)
from tests.utils import assert_logs, assert_not_logs

CHANGED_NAME = 'FOO BAR'
CHANGED_TEXT = 'Some good new text'
CHANGED_PROPERTIES = ['foo', 'bar']
LICENSE_TEXT = json.dumps({
    'MIT': {
        'name': CHANGED_NAME,
        'text': CHANGED_TEXT,
        'properties': CHANGED_PROPERTIES
    }
})

class TestNodeLicenses(OsfTestCase):

    def setUp(self):
        super(TestNodeLicenses, self).setUp()

        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        ensure_licenses()
        self.LICENSE_NAME = 'MIT License'
        self.node_license = NodeLicense.find_one(
            Q('name', 'eq', self.LICENSE_NAME)
        )
        self.YEAR = '2105'
        self.COPYRIGHT_HOLDERS = ['Foo', 'Bar']
        self.node.node_license = NodeLicenseRecordFactory(
            node_license=self.node_license,
            year=self.YEAR,
            copyright_holders=self.COPYRIGHT_HOLDERS
        )
        self.node.save()

    def test_serialize_node_license(self):
        serialized = serialize_node_license(self.node_license)
        assert_equal(serialized['name'], self.LICENSE_NAME)
        assert_equal(serialized['id'], self.node_license.id)
        assert_equal(serialized['text'], self.node_license.text)

    def test_serialize_node_license_record(self):
        serialized = serialize_node_license_record(self.node.node_license)
        assert_equal(serialized['name'], self.LICENSE_NAME)
        assert_equal(serialized['id'], self.node_license.id)
        assert_equal(serialized['text'], self.node_license.text)
        assert_equal(serialized['year'], self.YEAR)
        assert_equal(serialized['copyright_holders'], self.COPYRIGHT_HOLDERS)

    def test_serialize_node_license_record_None(self):
        self.node.node_license = None
        serialized = serialize_node_license_record(self.node.node_license)
        assert_equal(serialized, {})

    def test_copy_node_license_record(self):
        record = self.node.node_license
        copied = record.copy()
        assert_is_not_none(copied._id)
        assert_not_equal(record._id, copied._id)
        for prop in ('id', 'name', 'node_license'):
            assert_equal(getattr(record, prop), getattr(copied, prop))

    def test_ensure_licenses_existing_licenses(self):
        with mock.patch('website.project.licenses.NodeLicense.__init__', autospec=True) as MockNodeLicense:
            ensure_licenses()
        assert_false(MockNodeLicense.called)

    def test_ensure_licenses_no_licenses(self):
        before_count = NodeLicense.find().count()
        NodeLicense.remove()
        assert_false(NodeLicense.find().count())

        ensure_licenses()
        assert_equal(before_count, NodeLicense.find().count())

    def test_ensure_licenses_some_missing(self):
        NodeLicense.remove_one(
            Q('id', 'eq', 'LGPL3')
        )
        with assert_raises(NoResultsFound):
            NodeLicense.find_one(
                Q('id', 'eq', 'LGPL3')
            )            
        ensure_licenses()
        found = NodeLicense.find_one(
            Q('id', 'eq', 'LGPL3')
        )            
        assert_is_not_none(found)

    def test_ensure_licenses_updates_existing(self):
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=LICENSE_TEXT)):
            ensure_licenses()
        MIT = NodeLicense.find_one(
            Q('id', 'eq', 'MIT')
        )
        assert_equal(MIT.text, CHANGED_TEXT)
        assert_equal(MIT.properties, CHANGED_PROPERTIES)

    def test_ensure_licenses_updates_existing(self):
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=LICENSE_TEXT)):
            ensure_licenses()
        MIT = NodeLicense.find_one(
            Q('id', 'eq', 'MIT')
        )
        assert_equal(MIT.name, CHANGED_NAME)
        assert_equal(MIT.text, CHANGED_TEXT)
        assert_equal(MIT.properties, CHANGED_PROPERTIES)

    @assert_logs(NodeLog.CHANGED_LICENSE, 'node')
    def test_Node_set_node_license(self):
        GPL3 = NodeLicense.find_one(
            Q('id', 'eq', 'GPL3')
        )
        NEW_YEAR = '2014'
        COPYLEFT_HOLDERS = ['Richard Stallman']
        self.node.set_node_license('GPL3', NEW_YEAR, COPYLEFT_HOLDERS, auth=Auth(self.user))
        assert_equal(self.node.node_license.id, GPL3.id)
        assert_equal(self.node.node_license.name, GPL3.name)
        assert_equal(self.node.node_license.copyright_holders, COPYLEFT_HOLDERS)

    @assert_not_logs(NodeLog.CHANGED_LICENSE, 'node')
    def test_Node_set_node_license_invalid(self):
        invalid_license = {
            'id': 'SOME ID',
        }
        with assert_raises(NodeStateError):
            self.node.set_node_license(invalid_license['id'], 'foo', [], auth=Auth(self.user))
