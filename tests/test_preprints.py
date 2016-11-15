    # -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
from modularodm import Q
from modularodm.exceptions import NoResultsFound, ValidationValueError

from website.addons.osfstorage import settings as osfstorage_settings
from website.files.models.osfstorage import OsfStorageFile

from website.preprints.tasks import format_preprint
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
    PreprintProviderFactory,
    SubjectFactory
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
        assert_true(self.preprint.node.is_preprint)

    def test_preprint_is_public(self):
        assert_true(self.preprint.node.is_public)


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

        self.preprint = PreprintFactory(project=self.project, finish=False)

    @assert_logs(NodeLog.MADE_PUBLIC, 'project')
    @assert_logs(NodeLog.PREPRINT_INITIATED, 'project', -2)
    def test_is_preprint_property_new_file_to_published(self):
        assert_false(self.project.is_preprint)
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        self.project.reload()
        assert_false(self.project.is_preprint)
        with assert_raises(ValueError):
            self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.provider = PreprintProviderFactory()
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth, save=True)
        self.project.reload()
        assert_false(self.project.is_preprint)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.project.is_preprint)


    def test_project_made_public(self):
        assert_false(self.project.is_public)
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_false(self.project.is_public)
        with assert_raises(ValueError):
            self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.provider = PreprintProviderFactory()
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth, save=True)
        self.project.reload()
        assert_false(self.project.is_public)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.project.is_public)

    def test_add_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)
        assert_equal(type(self.project.preprint_file), type(self.file.stored_object))

    @assert_logs(NodeLog.PREPRINT_FILE_UPDATED, 'project')
    def test_change_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)

        self.preprint.set_primary_file(self.file_two, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(AttributeError):
            self.preprint.set_primary_file('inatlanta', auth=self.auth, save=True)

    def test_preprint_created_date(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        assert(self.preprint.date_created)
        assert_not_equal(self.project.date_created, self.preprint.date_created)

    def test_non_admin_update_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        with assert_raises(PermissionsError):
            self.preprint.set_primary_file(self.file_two, auth=self.read_write_user_auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)


class TestPreprintServicePermissions(OsfTestCase):
    def setUp(self):
        super(TestPreprintServicePermissions, self).setUp()
        self.user = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.write_contrib, permissions=[permissions.WRITE])

        self.preprint = PreprintFactory(project=self.project, is_published=False)


    def test_nonadmin_cannot_set_subjects(self):
        initial_subjects = self.preprint.subjects
        with assert_raises(PermissionsError):
            self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.write_contrib), save=True)

        self.preprint.reload()
        assert_equal(initial_subjects, self.preprint.subjects)

    def test_nonadmin_cannot_set_file(self):
        initial_file = self.preprint.primary_file
        file = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        file.save()
        
        with assert_raises(PermissionsError):
            self.preprint.set_primary_file(file, auth=Auth(self.write_contrib), save=True)

        self.preprint.reload()
        self.preprint.node.reload()
        assert_equal(initial_file._id, self.preprint.primary_file._id)

    def test_nonadmin_cannot_publish(self):
        assert_false(self.preprint.is_published)

        with assert_raises(PermissionsError):
            self.preprint.set_published(True, auth=Auth(self.write_contrib), save=True)

        assert_false(self.preprint.is_published)

    def test_admin_can_set_subjects(self):
        initial_subjects = self.preprint.subjects
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.user), save=True)

        self.preprint.reload()
        assert_not_equal(initial_subjects, self.preprint.subjects)

    def test_admin_can_set_file(self):
        initial_file = self.preprint.primary_file
        file = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        file.save()
        
        self.preprint.set_primary_file(file, auth=Auth(self.user), save=True)

        self.preprint.reload()
        self.preprint.node.reload()
        assert_not_equal(initial_file._id, self.preprint.primary_file._id)
        assert_equal(file._id, self.preprint.primary_file._id)

    def test_admin_can_publish(self):
        assert_false(self.preprint.is_published)

        self.preprint.set_published(True, auth=Auth(self.user), save=True)

        assert_true(self.preprint.is_published)

    def test_admin_cannot_unpublish(self):
        assert_false(self.preprint.is_published)

        self.preprint.set_published(True, auth=Auth(self.user), save=True)

        assert_true(self.preprint.is_published)

        with assert_raises(ValueError) as e:
            self.preprint.set_published(False, auth=Auth(self.user), save=True)

        assert_in('Cannot unpublish', e.exception.message)


class TestPreprintProviders(OsfTestCase):
    def setUp(self):
        super(TestPreprintProviders, self).setUp()
        self.preprint = PreprintFactory(providers=[])
        self.provider = PreprintProviderFactory(name='WWEArxiv')

    def test_add_provider(self):
        assert_not_equal(self.preprint.provider, self.provider)

        self.preprint.provider = self.provider
        self.preprint.save()
        self.preprint.reload()

        assert_equal(self.preprint.provider, self.provider)

    def test_remove_provider(self):
        self.preprint.provider = None
        self.preprint.save()
        self.preprint.reload()

        assert_equal(self.preprint.provider, None)

class TestOnPreprintUpdatedTask(OsfTestCase):
    def setUp(self):
        super(TestOnPreprintUpdatedTask, self).setUp()
        self.preprint = PreprintFactory()

    def test_format_preprint(self):
        res = format_preprint(self.preprint)
        types = [gn['@type'] for gn in res]
        subject_names = [x['text'] for hier in self.preprint.get_subjects() for x in hier]
        contribs = {}
        for i, user in enumerate(self.preprint.node.contributors):
            contribs.update({i: user})

        for type_ in ['throughlinks', 'throughsubjects', 'throughidentifiers', 'preprint', 'subject', 'person', 'link', 'contributor', 'identifier', 'person']:
            assert type_ in types

        for graph_node in res:
            if graph_node['@type'] == 'throughlinks':
                assert_equal(set(graph_node.keys()), set(['@id', '@type', 'creative_work', 'link']))
            if graph_node['@type'] == 'throughsubjects':
                assert_equal(set(graph_node.keys()), set(['@id', '@type', 'creative_work', 'subject']))
            if graph_node['@type'] == 'throughidentifiers':
                assert_equal(set(graph_node.keys()), set(['@id', '@type', 'identifier', 'person']))
            if graph_node['@type'] == 'preprint':
                assert_equal(set(graph_node.keys()), set([
                    '@id', '@type', 'contributors', 'title', 'tags',
                    'date_published', 'date_updated', 'description',
                    'institutions', 'is_deleted', 'links', 'subjects',
                ]))
                assert_equal(graph_node['date_published'], self.preprint.date_published.isoformat())
                assert_equal(graph_node['date_updated'], self.preprint.date_modified.isoformat())
                assert_equal(graph_node['description'], self.preprint.node.description)
                assert_equal(graph_node['is_deleted'], self.preprint.node.is_deleted)
                assert_equal(graph_node['title'], self.preprint.node.title)
            if graph_node['@type'] == 'subject':
                assert_equal(set(graph_node.keys()), set(['@id', '@type', 'name']))
                assert_in(graph_node['name'], subject_names)
            if graph_node['@type'] == 'person':
                assert_equal(set(graph_node.keys()), set([
                    '@id', '@type', 'additional_name', 'affiliations',
                    'family_name', 'given_name', 'identifiers', 'suffix'
                ]))
            if graph_node['@type'] == 'link':
                assert_equal(set(graph_node.keys()), set(['@id', '@type', 'type', 'url']))
            if graph_node['@type'] == 'contributor':
                assert_equal(set(graph_node.keys()), set([
                    '@id', '@type',  'bibliographic', 'cited_name',
                    'creative_work', 'order_cited', 'person'
                ]))
                user = contribs[graph_node['order_cited']]
                assert_equal(graph_node['cited_name'], user.fullname)
                assert_equal(graph_node['bibliographic'], bool(user._id in self.preprint.node.visible_contributor_ids))
            if graph_node['@type'] == 'identifier':
                assert_equal(set(graph_node.keys()), set(['@id', '@type', 'base_url', 'url']))
