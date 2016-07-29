# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from website.addons.osfstorage import settings as osfstorage_settings
from website.files.models.osfstorage import OsfStorageFile
from website.util import permissions


from framework.auth import Auth
from framework.exceptions import PermissionsError

from website import settings
from website.project.model import (
    NodeLog,
    NodeStateError
)

# ensure_taxonomies = functools.partial(ensure_taxonomies, warn=False)

from tests.base import OsfTestCase
from tests.factories import (
    AuthUserFactory,
    PreprintFactory
)
from tests.utils import assert_logs, assert_not_logs


class TestSetPreprintFile(OsfTestCase):

    def setUp(self):
        super(TestSetPreprintFile, self).setUp()

        self.user = AuthUserFactory()
        self.read_write_user = AuthUserFactory()
        self.read_write_user_auth = Auth(user=self.read_write_user)
        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory(creator=self.user)

        self.preprint.add_contributor(self.read_write_user, permissions=[permissions.WRITE])

        self.file = OsfStorageFile.create(
            is_file=True,
            node=self.preprint,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.guid = self.file.get_guid(create=True)
        self.file.save()

        self.file_two = OsfStorageFile.create(
            is_file=True,
            node=self.preprint,
            path='/pandapanda.txt',
            name='pandapanda.txt',
            materialized_path='/pandapanda.txt')
        self.guid = self.file.get_guid(create=True)
        self.file_two.save()

        # TODO - call ensure_taxonomies here?

        self.preprint.save()

    @assert_logs(NodeLog.PREPRINT_INITIATED, 'preprint')
    def test_add_primary_file(self):
        self.preprint.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.preprint.preprint_file._id, self.file._id)

    @assert_logs(NodeLog.PREPRINT_UPDATED, 'preprint')
    def test_change_primary_file(self):
        self.preprint.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.preprint.preprint_file._id, self.file._id)

        self.preprint.set_preprint_file(self.file_two._id, auth=self.auth, save=True)
        assert_equal(self.preprint.preprint_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(NodeStateError):
            self.preprint.set_preprint_file('inatlanta', auth=self.auth, save=True)

    def test_preprint_created_date(self):
        self.preprint.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.preprint.preprint_file._id, self.file._id)

        assert(self.preprint.preprint_created)
        assert_not_equal(self.preprint.date_created, self.preprint.preprint_created)

    def test_non_admin_update_file(self):
        self.preprint.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.preprint.preprint_file._id, self.file._id)

        with assert_raises(PermissionsError):
            self.preprint.set_preprint_file(self.file_two._id, auth=self.read_write_user_auth, save=True)
        assert_equal(self.preprint.preprint_file._id, self.file._id)
