#!/usr/bin/env python
# encoding: utf-8
import pytest
from nose.tools import *  # noqa


from framework import sessions
from framework.flask import request

from osf.models import Session
from addons.osfstorage.tests import factories
from addons.osfstorage import utils

from addons.osfstorage.tests.utils import StorageTestCase
from website.files.utils import attach_versions


@pytest.mark.django_db
class TestSerializeRevision(StorageTestCase):

    def setUp(self):
        super(TestSerializeRevision, self).setUp()
        self.path = 'kind-of-magic.webm'
        self.record = self.node_settings.get_root().append_file(self.path)
        self.versions = [
            factories.FileVersionFactory(creator=self.user)
            for __ in range(3)
        ]
        attach_versions(self.record, self.versions)
        self.record.save()

    def test_serialize_revision(self):
        sessions.sessions[request._get_current_object()] = Session()
        utils.update_analytics(self.project, self.record._id, 0)
        utils.update_analytics(self.project, self.record._id, 0)
        utils.update_analytics(self.project, self.record._id, 2)
        expected = {
            'index': 1,
            'user': {
                'name': self.user.fullname,
                'url': self.user.url,
            },
            'date': self.versions[0].created.isoformat(),
            'downloads': 2,
            'md5': None,
            'sha256': None,
        }
        observed = utils.serialize_revision(
            self.project,
            self.record,
            self.versions[0],
            0,
        )
        assert_equal(expected, observed)
        assert_equal(self.record.get_download_count(), 3)
        assert_equal(self.record.get_download_count(version=2), 1)
        assert_equal(self.record.get_download_count(version=0), 2)

    def test_anon_revisions(self):
        sessions.sessions[request._get_current_object()] = Session()
        utils.update_analytics(self.project, self.record._id, 0)
        utils.update_analytics(self.project, self.record._id, 0)
        utils.update_analytics(self.project, self.record._id, 2)
        expected = {
            'index': 2,
            'user': None,
            'date': self.versions[0].created.isoformat(),
            'downloads': 0,
            'md5': None,
            'sha256': None,
        }
        observed = utils.serialize_revision(
            self.project,
            self.record,
            self.versions[0],
            1,
            anon=True
        )
        assert_equal(expected, observed)
