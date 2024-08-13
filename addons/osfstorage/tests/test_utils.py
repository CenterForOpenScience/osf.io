#!/usr/bin/env python3
import pytest
from importlib import import_module

from django.conf import settings as django_conf_settings

from addons.osfstorage.tests import factories
from addons.osfstorage import utils

from addons.osfstorage.tests.utils import StorageTestCase
from website.files.utils import attach_versions

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore

@pytest.mark.django_db
class TestSerializeRevision(StorageTestCase):

    def setUp(self):
        super().setUp()
        self.path = 'kind-of-magic.webm'
        self.record = self.node_settings.get_root().append_file(self.path)
        self.versions = [
            factories.FileVersionFactory(creator=self.user)
            for __ in range(3)
        ]
        attach_versions(self.record, self.versions)
        self.record.save()

    def test_serialize_revision(self):
        s = SessionStore()
        s.create()
        utils.update_analytics(self.project, self.record, 0, s.session_key)
        utils.update_analytics(self.project, self.record, 0, s.session_key)
        utils.update_analytics(self.project, self.record, 2, s.session_key)
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
        assert expected == observed
        assert self.record.get_download_count() == 3
        assert self.record.get_download_count(version=2) == 1
        assert self.record.get_download_count(version=0) == 2

    def test_anon_revisions(self):
        s = SessionStore()
        s.create()
        utils.update_analytics(self.project, self.record, 0, s.session_key)
        utils.update_analytics(self.project, self.record, 0, s.session_key)
        utils.update_analytics(self.project, self.record, 2, s.session_key)
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
        assert expected == observed
