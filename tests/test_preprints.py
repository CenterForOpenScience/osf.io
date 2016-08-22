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


from tests.base import OsfTestCase
from tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    PreprintFactory,
    PreprintProviderFactory
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

        self.project.add_contributor(self.read_write_user, permissions=[permissions.WRITE])
        self.project.save()

    @assert_logs(NodeLog.MADE_PUBLIC, 'project')
    @assert_logs(NodeLog.PREPRINT_INITIATED, 'project', -2)
    def test_is_preprint_property_new_file(self):
        self.project.set_preprint_file(self.file, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.project.is_preprint)

    def test_project_made_public(self):
        assert_false(self.project.is_public)
        self.project.set_preprint_file(self.file, auth=self.auth, save=True)
        assert_true(self.project.is_public)

    def test_add_primary_file(self):
        self.project.set_preprint_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)
        assert_equal(type(self.project.preprint_file), type(self.file.stored_object))

    @assert_logs(NodeLog.PREPRINT_FILE_UPDATED, 'project')
    def test_change_primary_file(self):
        self.project.set_preprint_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)

        self.project.set_preprint_file(self.file_two, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(AttributeError):
            self.project.set_preprint_file('inatlanta', auth=self.auth, save=True)

    def test_preprint_created_date(self):
        self.project.set_preprint_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        assert(self.project.preprint_created)
        assert_not_equal(self.project.date_created, self.project.preprint_created)

    def test_non_admin_update_file(self):
        self.project.set_preprint_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        with assert_raises(PermissionsError):
            self.project.set_preprint_file(self.file_two, auth=self.read_write_user_auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)


class TestPreprintProviders(OsfTestCase):
    def setUp(self):
        super(TestPreprintProviders, self).setUp()
        self.preprint = PreprintFactory(providers=[])
        self.provider = PreprintProviderFactory(name='WWEArxiv')

    def test_add_provider(self):
        assert_equal(self.preprint.preprint_providers, [])

        self.preprint.add_preprint_provider(self.provider, user=self.preprint.creator, save=True)

        assert_items_equal(self.preprint.preprint_providers, [self.provider])

    def test_remove_provider(self):
        self.preprint.add_preprint_provider(self.provider, user=self.preprint.creator, save=True)

        assert_items_equal(self.preprint.preprint_providers, [self.provider])

        self.preprint.remove_preprint_provider(self.provider, user=self.preprint.creator, save=True)

        assert_equal(self.preprint.preprint_providers, [])
