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
    ProjectFactory,
    PreprintFactory
)
from tests.utils import assert_logs, assert_not_logs


class TestPreprintFactory(OsfTestCase):
    def setUp(self):
        super(TestPreprintFactory, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory(creator=self.user)
        self.preprint.save()

    def test_is_preprint(self):
        assert_true(self.preprint.is_preprint)

    def test_preprint_is_public(self):
        assert_true(self.preprint.is_public)


class TestSetPreprintFile(OsfTestCase):

    def setUp(self):
        super(TestSetPreprintFile, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.read_write_user = AuthUserFactory()
        self.read_write_user_auth = Auth(user=self.read_write_user)

        self.project = ProjectFactory(creator=self.user)
        self.file = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()

        self.file_two = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/pandapanda.txt',
            name='pandapanda.txt',
            materialized_path='/pandapanda.txt')
        self.file_two.save()

        # TODO - call ensure_taxonomies here?

        self.project.add_contributor(self.read_write_user, permissions=[permissions.WRITE])
        self.project.save()

    def test_is_preprint_property_new_file(self):
        self.project.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_true(self.project.is_preprint)

    def test_project_made_public(self):
        assert_false(self.project.is_public)
        self.project.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_true(self.project.is_public)

    def test_add_primary_file(self):
        self.project.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

    @assert_logs(NodeLog.PREPRINT_UPDATED, 'project')
    def test_change_primary_file(self):
        self.project.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        self.project.set_preprint_file(self.file_two._id, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(NodeStateError):
            self.project.set_preprint_file('inatlanta', auth=self.auth, save=True)

    def test_preprint_created_date(self):
        self.project.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        assert(self.project.preprint_created)
        assert_not_equal(self.project.date_created, self.project.preprint_created)

    def test_non_admin_update_file(self):
        self.project.set_preprint_file(self.file._id, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        with assert_raises(PermissionsError):
            self.project.set_preprint_file(self.file_two._id, auth=self.read_write_user_auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)
