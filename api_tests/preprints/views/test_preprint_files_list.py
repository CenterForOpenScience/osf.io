import datetime
import json

import furl
import responses
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from api.base.settings.defaults import API_BASE
from api.base.utils import waterbutler_api_url_for
from api_tests import utils as api_utils
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PreprintFactory
)
from osf.utils.workflows import DefaultStates
from addons.osfstorage.models import OsfStorageFile


class TestPreprintFilesList(ApiTestCase):

    def setUp(self):
        super(TestPreprintFilesList, self).setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/{}/files/'.format(API_BASE, self.preprint._id)
        self.user_two = AuthUserFactory()

    def test_published_preprint_files(self):
        # Unauthenticated
        res = self.app.get(self.url)
        assert res.status_code == 200

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Write contributor
        self.preprint.add_contributor(self.user_two, 'write', save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_unpublished_preprint_files(self):
        self.preprint.is_published = False
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, 'write', save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_private_preprint_files(self):
        self.preprint.is_public = False
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, 'write', save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_abandoned_preprint_files(self):
        self.preprint.machine_state = DefaultStates.INITIAL.value
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, 'write', save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_orphaned_preprint_files(self):
        self.preprint.primary_file = None
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, 'write', save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_deleted_preprint_files(self):
        self.preprint.deleted = timezone.now()
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 404

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 404

        # Write contributor
        self.preprint.add_contributor(self.user_two, 'write', save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 404

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_only_primary_file_is_returned(self):
        filename = 'my second file'
        second_file = OsfStorageFile.create(
            target_object_id=self.preprint.id,
            target_content_type=ContentType.objects.get_for_model(self.preprint),
            path='/{}'.format(filename),
            name=filename,
            materialized_path='/{}'.format(filename))

        second_file.save()
        from addons.osfstorage import settings as osfstorage_settings

        second_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()
        second_file.parent = self.preprint.root_folder
        second_file.save()

        assert len(self.preprint.files.all()) == 2
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

        data = res.json['data']
        assert len(data) == 1
        assert data[0]['id'] == self.preprint.primary_file._id
