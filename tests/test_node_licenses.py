import builtins
import json
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from framework.auth import Auth
from osf_tests.factories import (AuthUserFactory, NodeLicenseRecordFactory,
                                 ProjectFactory)
from tests.base import OsfTestCase
from osf.utils.migrations import ensure_licenses
from tests.utils import assert_logs, assert_not_logs
from website import settings
from osf.models.licenses import NodeLicense, serialize_node_license_record, serialize_node_license
from osf.models import NodeLog
from osf.exceptions import NodeStateError



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
        super().setUp()

        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.LICENSE_NAME = 'MIT License'
        self.node_license = NodeLicense.objects.get(name=self.LICENSE_NAME)
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
        assert serialized['name'] == self.LICENSE_NAME
        assert serialized['id'] == self.node_license.license_id
        assert serialized['text'] == self.node_license.text

    def test_serialize_node_license_record(self):
        serialized = serialize_node_license_record(self.node.node_license)
        assert serialized['name'] == self.LICENSE_NAME
        assert serialized['id'] == self.node_license.license_id
        assert serialized['text'] == self.node_license.text
        assert serialized['year'] == self.YEAR
        assert serialized['copyright_holders'] == self.COPYRIGHT_HOLDERS

    def test_serialize_node_license_record_None(self):
        self.node.node_license = None
        serialized = serialize_node_license_record(self.node.node_license)
        assert serialized == {}

    def test_copy_node_license_record(self):
        record = self.node.node_license
        copied = record.copy()
        assert copied._id is not None
        assert record._id != copied._id
        for prop in ('license_id', 'name', 'node_license'):
            assert getattr(record, prop) == getattr(copied, prop)

    @pytest.mark.enable_implicit_clean
    def test_license_uniqueness_on_id_is_enforced_in_the_database(self):
        NodeLicense(license_id='foo', name='bar', text='baz').save()
        pytest.raises(ValidationError, NodeLicense(license_id='foo', name='buz', text='boo').save)

    def test_ensure_licenses_updates_existing_licenses(self):
        assert ensure_licenses() == (0, 18)

    def test_ensure_licenses_no_licenses(self):
        before_count = NodeLicense.objects.all().count()
        NodeLicense.objects.all().delete()
        assert not NodeLicense.objects.all().count()

        ensure_licenses()
        assert before_count == NodeLicense.objects.all().count()

    def test_ensure_licenses_some_missing(self):
        NodeLicense.objects.get(license_id='LGPL3').delete()
        with pytest.raises(NodeLicense.DoesNotExist):
            NodeLicense.objects.get(license_id='LGPL3')
        ensure_licenses()
        found = NodeLicense.objects.get(license_id='LGPL3')
        assert found is not None

    def test_ensure_licenses_updates_existing(self):
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=LICENSE_TEXT)):
            ensure_licenses()
        MIT = NodeLicense.objects.get(license_id='MIT')
        assert MIT.name == CHANGED_NAME
        assert MIT.text == CHANGED_TEXT
        assert MIT.properties == CHANGED_PROPERTIES

    @assert_logs(NodeLog.CHANGED_LICENSE, 'node')
    def test_Node_set_node_license(self):
        GPL3 = NodeLicense.objects.get(license_id='GPL3')
        NEW_YEAR = '2014'
        COPYLEFT_HOLDERS = ['Richard Stallman']
        self.node.set_node_license(
            {
                'id': GPL3.license_id,
                'year': NEW_YEAR,
                'copyrightHolders': COPYLEFT_HOLDERS
            },
            auth=Auth(self.user),
            save=True
        )

        assert self.node.node_license.license_id == GPL3.license_id
        assert self.node.node_license.name == GPL3.name
        assert self.node.node_license.copyright_holders == COPYLEFT_HOLDERS

    @assert_not_logs(NodeLog.CHANGED_LICENSE, 'node')
    def test_Node_set_node_license_invalid(self):
        with pytest.raises(NodeStateError):
            self.node.set_node_license(
                {
                    'id': 'SOME ID',
                    'year': 'foo',
                    'copyrightHolders': []
                },
                auth=Auth(self.user)
            )
