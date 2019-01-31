# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import mock
import time
import unittest
import logging
import functools

from nose.tools import *  # noqa: F403
import pytest

from framework.auth.core import Auth

from website import settings
import website.search.search as search
from website.search import elastic_search
from website.search.util import build_query
from website.search_migration.migrate import migrate
from osf.models import (
    Retraction,
    NodeLicense,
    Tag,
    Preprint,
    QuickFilesNode,
)
from addons.wiki.models import WikiPage
from addons.osfstorage.models import OsfStorageFile

from scripts.populate_institutions import main as populate_institutions

from osf_tests import factories
from tests.base import OsfTestCase
from tests.test_features import requires_search
from tests.utils import run_celery_tasks


TEST_INDEX = 'test'

def query(term, raw=False):
    results = search.search(build_query(term), index=elastic_search.INDEX, raw=raw)
    return results

def query_collections(name):
    term = 'category:collectionSubmission AND "{}"'.format(name)
    return query(term, raw=True)

def query_user(name):
    term = 'category:user AND "{}"'.format(name)
    return query(term)

def query_file(name):
    term = 'category:file AND "{}"'.format(name)
    return query(term)

def query_tag_file(name):
    term = 'category:file AND (tags:u"{}")'.format(name)
    return query(term)

def retry_assertion(interval=0.3, retries=3):
    def test_wrapper(func):
        t_interval = interval
        t_retries = retries

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except AssertionError as e:
                if retries:
                    time.sleep(t_interval)
                    retry_assertion(interval=t_interval, retries=t_retries - 1)(func)(*args, **kwargs)
                else:
                    raise e
        return wrapped
    return test_wrapper

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestCollectionsSearch(OsfTestCase):
    def setUp(self):
        super(TestCollectionsSearch, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)

        self.user = factories.UserFactory(fullname='Salif Keita')
        self.node_private = factories.NodeFactory(creator=self.user, title='Salif Keita: Madan', is_public=False)
        self.node_public = factories.NodeFactory(creator=self.user, title='Salif Keita: Yamore', is_public=True)
        self.node_one = factories.NodeFactory(creator=self.user, title='Salif Keita: Mandjou', is_public=True)
        self.node_two = factories.NodeFactory(creator=self.user, title='Salif Keita: Tekere', is_public=True)
        self.reg_private = factories.RegistrationFactory(title='Salif Keita: Madan', creator=self.user, is_public=False)
        self.reg_public = factories.RegistrationFactory(title='Salif Keita: Madan', creator=self.user, is_public=True)
        self.reg_one = factories.RegistrationFactory(title='Salif Keita: Madan', creator=self.user, is_public=True)
        self.provider = factories.CollectionProviderFactory()
        self.reg_provider = factories.RegistrationProviderFactory()
        self.collection_one = factories.CollectionFactory(creator=self.user, is_public=True, provider=self.provider)
        self.collection_public = factories.CollectionFactory(creator=self.user, is_public=True, provider=self.provider)
        self.collection_private = factories.CollectionFactory(creator=self.user, is_public=False, provider=self.provider)
        self.reg_collection = factories.CollectionFactory(creator=self.user, provider=self.reg_provider, is_public=True)
        self.reg_collection_private = factories.CollectionFactory(creator=self.user, provider=self.reg_provider, is_public=False)

    def test_only_public_collections_submissions_are_searchable(self):
        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        self.collection_public.collect_object(self.node_private, self.user)
        self.reg_collection.collect_object(self.reg_private, self.user)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        assert_false(self.node_one.is_collected)
        assert_false(self.node_public.is_collected)

        self.collection_one.collect_object(self.node_one, self.user)
        self.collection_public.collect_object(self.node_public, self.user)
        self.reg_collection.collect_object(self.reg_public, self.user)

        assert_true(self.node_one.is_collected)
        assert_true(self.node_public.is_collected)
        assert_true(self.reg_public.is_collected)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 3)

        self.collection_private.collect_object(self.node_two, self.user)
        self.reg_collection_private.collect_object(self.reg_one, self.user)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 3)

    def test_index_on_submission_privacy_changes(self):
        # test_submissions_turned_private_are_deleted_from_index
        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        self.collection_public.collect_object(self.node_one, self.user)
        self.collection_one.collect_object(self.node_one, self.user)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 2)

        with run_celery_tasks():
            self.node_one.is_public = False
            self.node_one.save()

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        # test_submissions_turned_public_are_added_to_index
        self.collection_public.collect_object(self.node_private, self.user)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        with run_celery_tasks():
            self.node_private.is_public = True
            self.node_private.save()

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 1)

    def test_index_on_collection_privacy_changes(self):
        # test_submissions_of_collection_turned_private_are_removed_from_index
        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        self.collection_public.collect_object(self.node_one, self.user)
        self.collection_public.collect_object(self.node_two, self.user)
        self.collection_public.collect_object(self.node_public, self.user)
        self.reg_collection.collect_object(self.reg_public, self.user)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 4)

        with run_celery_tasks():
            self.collection_public.is_public = False
            self.collection_public.save()
            self.reg_collection.is_public = False
            self.reg_collection.save()

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        # test_submissions_of_collection_turned_public_are_added_to_index
        self.collection_private.collect_object(self.node_one, self.user)
        self.collection_private.collect_object(self.node_two, self.user)
        self.collection_private.collect_object(self.node_public, self.user)
        self.reg_collection_private.collect_object(self.reg_public, self.user)

        assert_true(self.node_one.is_collected)
        assert_true(self.node_two.is_collected)
        assert_true(self.node_public.is_collected)
        assert_true(self.reg_public.is_collected)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        with run_celery_tasks():
            self.collection_private.is_public = True
            self.collection_private.save()
            self.reg_collection.is_public = True
            self.reg_collection.save()

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 4)

    def test_collection_submissions_are_removed_from_index_on_delete(self):
        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

        self.collection_public.collect_object(self.node_one, self.user)
        self.collection_public.collect_object(self.node_two, self.user)
        self.collection_public.collect_object(self.node_public, self.user)
        self.reg_collection.collect_object(self.reg_public, self.user)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 4)
        self.collection_public.delete()
        self.reg_collection.delete()

        assert_true(self.collection_public.deleted)
        assert_true(self.reg_collection.deleted)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

    def test_removed_submission_are_removed_from_index(self):
        self.collection_public.collect_object(self.node_one, self.user)
        self.reg_collection.collect_object(self.reg_public, self.user)
        assert_true(self.node_one.is_collected)
        assert_true(self.reg_public.is_collected)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 2)

        self.collection_public.remove_object(self.node_one)
        self.reg_collection.remove_object(self.reg_public)
        assert_false(self.node_one.is_collected)
        assert_false(self.reg_public.is_collected)

        docs = query_collections('Salif Keita')['results']
        assert_equal(len(docs), 0)

    def test_collection_submission_doc_structure(self):
        self.collection_public.collect_object(self.node_one, self.user)
        docs = query_collections('Keita')['results']
        assert_equal(docs[0]['_source']['title'], self.node_one.title)
        with run_celery_tasks():
            self.node_one.title = 'Keita Royal Family of Mali'
            self.node_one.save()
        docs = query_collections('Keita')['results']
        assert_equal(docs[0]['_source']['title'], self.node_one.title)
        assert_equal(docs[0]['_source']['abstract'], self.node_one.description)
        assert_equal(docs[0]['_source']['contributors'][0]['url'], self.user.url)
        assert_equal(docs[0]['_source']['contributors'][0]['fullname'], self.user.fullname)
        assert_equal(docs[0]['_source']['url'], self.node_one.url)
        assert_equal(docs[0]['_source']['id'], '{}-{}'.format(self.node_one._id,
            self.node_one.collecting_metadata_list[0].collection._id))
        assert_equal(docs[0]['_source']['category'], 'collectionSubmission')


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestUserUpdate(OsfTestCase):

    def setUp(self):
        super(TestUserUpdate, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
        self.user = factories.UserFactory(fullname='David Bowie')

    def test_new_user(self):
        # Verify that user has been added to Elastic Search
        docs = query_user(self.user.fullname)['results']
        assert_equal(len(docs), 1)

    def test_new_user_unconfirmed(self):
        user = factories.UnconfirmedUserFactory()
        docs = query_user(user.fullname)['results']
        assert_equal(len(docs), 0)
        token = user.get_confirmation_token(user.username)
        user.confirm_email(token)
        user.save()
        docs = query_user(user.fullname)['results']
        assert_equal(len(docs), 1)

    def test_change_name(self):
        # Add a user, change her name, and verify that only the new name is
        # found in search.
        user = factories.UserFactory(fullname='Barry Mitchell')
        fullname_original = user.fullname
        user.fullname = user.fullname[::-1]
        user.save()

        docs_original = query_user(fullname_original)['results']
        assert_equal(len(docs_original), 0)

        docs_current = query_user(user.fullname)['results']
        assert_equal(len(docs_current), 1)

    def test_disabled_user(self):
        # Test that disabled users are not in search index

        user = factories.UserFactory(fullname='Bettie Page')
        user.save()

        # Ensure user is in search index
        assert_equal(len(query_user(user.fullname)['results']), 1)

        # Disable the user
        user.is_disabled = True
        user.save()

        # Ensure user is not in search index
        assert_equal(len(query_user(user.fullname)['results']), 0)

    @pytest.mark.enable_quickfiles_creation
    def test_merged_user(self):
        user = factories.UserFactory(fullname='Annie Lennox')
        merged_user = factories.UserFactory(fullname='Lisa Stansfield')
        user.save()
        merged_user.save()
        assert_equal(len(query_user(user.fullname)['results']), 1)
        assert_equal(len(query_user(merged_user.fullname)['results']), 1)

        user.merge_user(merged_user)

        assert_equal(len(query_user(user.fullname)['results']), 1)
        assert_equal(len(query_user(merged_user.fullname)['results']), 0)

    def test_employment(self):
        user = factories.UserFactory(fullname='Helga Finn')
        user.save()
        institution = 'Finn\'s Fine Filers'

        docs = query_user(institution)['results']
        assert_equal(len(docs), 0)
        user.jobs.append({
            'institution': institution,
            'title': 'The Big Finn',
        })
        user.save()

        docs = query_user(institution)['results']
        assert_equal(len(docs), 1)

    def test_education(self):
        user = factories.UserFactory(fullname='Henry Johnson')
        user.save()
        institution = 'Henry\'s Amazing School!!!'

        docs = query_user(institution)['results']
        assert_equal(len(docs), 0)
        user.schools.append({
            'institution': institution,
            'degree': 'failed all classes',
        })
        user.save()

        docs = query_user(institution)['results']
        assert_equal(len(docs), 1)

    def test_name_fields(self):
        names = ['Bill Nye', 'William', 'the science guy', 'Sanford', 'the Great']
        user = factories.UserFactory(fullname=names[0])
        user.given_name = names[1]
        user.middle_names = names[2]
        user.family_name = names[3]
        user.suffix = names[4]
        user.save()
        docs = [query_user(name)['results'] for name in names]
        assert_equal(sum(map(len, docs)), len(docs))  # 1 result each
        assert_true(all([user._id == doc[0]['id'] for doc in docs]))


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestProject(OsfTestCase):

    def setUp(self):
        super(TestProject, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
        self.user = factories.UserFactory(fullname='John Deacon')
        self.project = factories.ProjectFactory(title='Red Special', creator=self.user)

    def test_new_project_private(self):
        # Verify that a private project is not present in Elastic Search.
        docs = query(self.project.title)['results']
        assert_equal(len(docs), 0)

    def test_make_public(self):
        # Make project public, and verify that it is present in Elastic
        # Search.
        with run_celery_tasks():
            self.project.set_privacy('public')
        docs = query(self.project.title)['results']
        assert_equal(len(docs), 1)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestPreprint(OsfTestCase):

    def setUp(self):
        with run_celery_tasks():
            super(TestPreprint, self).setUp()
            search.delete_index(elastic_search.INDEX)
            search.create_index(elastic_search.INDEX)
            self.user = factories.UserFactory(fullname='John Deacon')
            self.preprint = Preprint(
                title='Red Special',
                description='We are the champions',
                creator=self.user,
                provider=factories.PreprintProviderFactory()
            )
            self.preprint.save()
            self.file = OsfStorageFile.create(
                target=self.preprint,
                path='/panda.txt',
                name='panda.txt',
                materialized_path='/panda.txt')
            self.file.save()
            self.published_preprint = factories.PreprintFactory(
                creator=self.user,
                title='My Fairy King',
                description='Under pressure',
            )

    def test_new_preprint_unsubmitted(self):
        # Verify that an unsubmitted preprint is not present in Elastic Search.
        title = 'Apple'
        self.preprint.title = title
        self.preprint.save()
        docs = query(title)['results']
        assert_equal(len(docs), 0)

    def test_new_preprint_unpublished(self):
        # Verify that an unpublished preprint is not present in Elastic Search.
        title = 'Banana'
        self.preprint = factories.PreprintFactory(creator=self.user, is_published=False, title=title)
        assert self.preprint.title == title
        docs = query(title)['results']
        assert_equal(len(docs), 0)

    def test_unsubmitted_preprint_primary_file(self):
        # Unpublished preprint's primary_file not showing up in Elastic Search
        title = 'Cantaloupe'
        self.preprint.title = title
        self.preprint.set_primary_file(self.file, auth=Auth(self.user), save=True)
        assert self.preprint.title == title
        docs = query(title)['results']
        assert_equal(len(docs), 0)

    def test_publish_preprint(self):
        title = 'Date'
        self.preprint = factories.PreprintFactory(creator=self.user, is_published=False, title=title)
        self.preprint.set_published(True, auth=Auth(self.preprint.creator), save=True)
        assert self.preprint.title == title
        docs = query(title)['results']
        # Both preprint and primary_file showing up in Elastic
        assert_equal(len(docs), 2)

    def test_preprint_title_change(self):
        title_original = self.published_preprint.title
        new_title = 'New preprint title'
        self.published_preprint.set_title(new_title, auth=Auth(self.user), save=True)
        docs = query('category:preprint AND ' + title_original)['results']
        assert_equal(len(docs), 0)

        docs = query('category:preprint AND ' + new_title)['results']
        assert_equal(len(docs), 1)

    def test_preprint_description_change(self):
        description_original = self.published_preprint.description
        new_abstract = 'My preprint abstract'
        self.published_preprint.set_description(new_abstract, auth=Auth(self.user), save=True)
        docs = query(self.published_preprint.title)['results']
        docs = query('category:preprint AND ' + description_original)['results']
        assert_equal(len(docs), 0)

        docs = query('category:preprint AND ' + new_abstract)['results']
        assert_equal(len(docs), 1)

    def test_set_preprint_private(self):
        # Not currently an option for users, but can be used for spam
        self.published_preprint.set_privacy('private', auth=Auth(self.user), save=True)
        docs = query(self.published_preprint.title)['results']
        # Both preprint and primary_file showing up in Elastic
        assert_equal(len(docs), 0)

    def test_set_primary_file(self):
        # Only primary_file should be in index, if primary_file is changed, other files are removed from index.
        self.file = OsfStorageFile.create(
            target=self.published_preprint,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()
        self.published_preprint.set_primary_file(self.file, auth=Auth(self.user), save=True)
        docs = query(self.published_preprint.title)['results']
        assert_equal(len(docs), 2)
        assert_equal(docs[1]['name'], self.file.name)

    def test_set_license(self):
        license_details = {
            'id': 'NONE',
            'year': '2015',
            'copyrightHolders': ['Iron Man']
        }
        title = 'Elderberry'
        self.published_preprint.title = title
        self.published_preprint.set_preprint_license(license_details, Auth(self.user), save=True)
        assert self.published_preprint.title == title
        docs = query(title)['results']
        assert_equal(len(docs), 2)
        assert_equal(docs[0]['license']['copyright_holders'][0], 'Iron Man')
        assert_equal(docs[0]['license']['name'], 'No license')

    def test_add_tags(self):

        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

        for tag in tags:
            docs = query('tags:"{}"'.format(tag))['results']
            assert_equal(len(docs), 0)
            self.published_preprint.add_tag(tag, Auth(self.user), save=True)

        for tag in tags:
            docs = query('tags:"{}"'.format(tag))['results']
            assert_equal(len(docs), 1)

    def test_remove_tag(self):

        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

        for tag in tags:
            self.published_preprint.add_tag(tag, Auth(self.user), save=True)
            self.published_preprint.remove_tag(tag, Auth(self.user), save=True)
            docs = query('tags:"{}"'.format(tag))['results']
            assert_equal(len(docs), 0)

    def test_add_contributor(self):
        # Add a contributor, then verify that project is found when searching
        # for contributor.
        user2 = factories.UserFactory(fullname='Adam Lambert')

        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)
        # with run_celery_tasks():
        self.published_preprint.add_contributor(user2, save=True)

        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)

    def test_remove_contributor(self):
        # Add and remove a contributor, then verify that project is not found
        # when searching for contributor.
        user2 = factories.UserFactory(fullname='Brian May')

        self.published_preprint.add_contributor(user2, save=True)
        self.published_preprint.remove_contributor(user2, Auth(self.user))

        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)

    def test_hide_contributor(self):
        user2 = factories.UserFactory(fullname='Brian May')
        self.published_preprint.add_contributor(user2)
        self.published_preprint.set_visible(user2, False, save=True)
        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)
        self.published_preprint.set_visible(user2, True, save=True)
        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)

    def test_move_contributor(self):
        user2 = factories.UserFactory(fullname='Brian May')
        self.published_preprint.add_contributor(user2, save=True)
        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)
        docs[0]['contributors'][0]['fullname'] == self.user.fullname
        docs[0]['contributors'][1]['fullname'] == user2.fullname
        self.published_preprint.move_contributor(user2, Auth(self.user), 0)
        docs = query('category:preprint AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)
        docs[0]['contributors'][0]['fullname'] == user2.fullname
        docs[0]['contributors'][1]['fullname'] == self.user.fullname

    def test_tag_aggregation(self):
        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

        for tag in tags:
            self.published_preprint.add_tag(tag, Auth(self.user), save=True)

        docs = query(self.published_preprint.title)['tags']
        assert len(docs) == 3
        for doc in docs:
            assert doc['key'] in tags


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestNodeSearch(OsfTestCase):

    def setUp(self):
        super(TestNodeSearch, self).setUp()
        with run_celery_tasks():
            self.node = factories.ProjectFactory(is_public=True, title='node')
            self.public_child = factories.ProjectFactory(parent=self.node, is_public=True, title='public_child')
            self.private_child = factories.ProjectFactory(parent=self.node, title='private_child')
            self.public_subchild = factories.ProjectFactory(parent=self.private_child, is_public=True)
            self.node.node_license = factories.NodeLicenseRecordFactory()
            self.node.save()

        self.query = 'category:project & category:component'

    @retry_assertion()
    def test_node_license_added_to_search(self):
        docs = query(self.query)['results']
        node = [d for d in docs if d['title'] == self.node.title][0]
        assert_in('license', node)
        assert_equal(node['license']['id'], self.node.node_license.license_id)

    @unittest.skip('Elasticsearch latency seems to be causing theses tests to fail randomly.')
    @retry_assertion(retries=10)
    def test_node_license_propogates_to_children(self):
        docs = query(self.query)['results']
        child = [d for d in docs if d['title'] == self.public_child.title][0]
        assert_in('license', child)
        assert_equal(child['license'].get('id'), self.node.node_license.license_id)
        child = [d for d in docs if d['title'] == self.public_subchild.title][0]
        assert_in('license', child)
        assert_equal(child['license'].get('id'), self.node.node_license.license_id)

    @unittest.skip('Elasticsearch latency seems to be causing theses tests to fail randomly.')
    @retry_assertion(retries=10)
    def test_node_license_updates_correctly(self):
        other_license = NodeLicense.objects.get(name='MIT License')
        new_license = factories.NodeLicenseRecordFactory(node_license=other_license)
        self.node.node_license = new_license
        self.node.save()
        docs = query(self.query)['results']
        for doc in docs:
            assert_equal(doc['license'].get('id'), new_license.license_id)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestRegistrationRetractions(OsfTestCase):

    def setUp(self):
        super(TestRegistrationRetractions, self).setUp()
        self.user = factories.UserFactory(fullname='Doug Bogie')
        self.title = 'Red Special'
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory(
            title=self.title,
            description='',
            creator=self.user,
            is_public=True,
        )
        self.registration = factories.RegistrationFactory(project=self.project, is_public=True)

    @mock.patch('website.project.tasks.update_node_share')
    @mock.patch('osf.models.registrations.Registration.archiving', mock.PropertyMock(return_value=False))
    def test_retraction_is_searchable(self, mock_registration_updated):
        self.registration.retract_registration(self.user)
        self.registration.retraction.state = Retraction.APPROVED
        self.registration.retraction.save()
        self.registration.save()
        self.registration.retraction._on_complete(self.user)
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

    @mock.patch('osf.models.registrations.Registration.archiving', mock.PropertyMock(return_value=False))
    def test_pending_retraction_wiki_content_is_searchable(self):
        # Add unique string to wiki
        wiki_content = {'home': 'public retraction test'}
        for key, value in wiki_content.items():
            docs = query(value)['results']
            assert_equal(len(docs), 0)
            with run_celery_tasks():
                WikiPage.objects.create_for_node(self.registration, key, value, self.consolidate_auth)
            # Query and ensure unique string shows up
            docs = query(value)['results']
            assert_equal(len(docs), 1)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

        # Retract registration
        self.registration.retract_registration(self.user, '')
        with run_celery_tasks():
            self.registration.save()
            self.registration.reload()

        # Query and ensure unique string in wiki doesn't show up
        docs = query('category:registration AND "{}"'.format(wiki_content['home']))['results']
        assert_equal(len(docs), 1)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

    @mock.patch('osf.models.registrations.Registration.archiving', mock.PropertyMock(return_value=False))
    def test_retraction_wiki_content_is_not_searchable(self):
        # Add unique string to wiki
        wiki_content = {'home': 'public retraction test'}
        for key, value in wiki_content.items():
            docs = query(value)['results']
            assert_equal(len(docs), 0)
            with run_celery_tasks():
                WikiPage.objects.create_for_node(self.registration, key, value, self.consolidate_auth)
            # Query and ensure unique string shows up
            docs = query(value)['results']
            assert_equal(len(docs), 1)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

        # Retract registration
        self.registration.retract_registration(self.user, '')
        self.registration.retraction.state = Retraction.APPROVED
        with run_celery_tasks():
            self.registration.retraction.save()
            self.registration.save()
            self.registration.update_search()

        # Query and ensure unique string in wiki doesn't show up
        docs = query('category:registration AND "{}"'.format(wiki_content['home']))['results']
        assert_equal(len(docs), 0)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestPublicNodes(OsfTestCase):

    def setUp(self):
        with run_celery_tasks():
            super(TestPublicNodes, self).setUp()
            self.user = factories.UserFactory(fullname='Doug Bogie')
            self.title = 'Red Special'
            self.consolidate_auth = Auth(user=self.user)
            self.project = factories.ProjectFactory(
                title=self.title,
                description='',
                creator=self.user,
                is_public=True,
            )
            self.component = factories.NodeFactory(
                parent=self.project,
                description='',
                title=self.title,
                creator=self.user,
                is_public=True
            )
            self.registration = factories.RegistrationFactory(
                title=self.title,
                description='',
                creator=self.user,
                is_public=True,
            )
            self.registration.archive_job.target_addons = []
            self.registration.archive_job.status = 'SUCCESS'
            self.registration.archive_job.save()

    def test_make_private(self):
        # Make project public, then private, and verify that it is not present
        # in search.
        with run_celery_tasks():
            self.project.set_privacy('private')
        docs = query('category:project AND ' + self.title)['results']
        assert_equal(len(docs), 0)

        with run_celery_tasks():
            self.component.set_privacy('private')
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    def test_search_node_partial(self):
        self.project.set_title('Blue Rider-Express', self.consolidate_auth)
        with run_celery_tasks():
            self.project.save()
        find = query('Blue')['results']
        assert_equal(len(find), 1)

    def test_search_node_partial_with_sep(self):
        self.project.set_title('Blue Rider-Express', self.consolidate_auth)
        with run_celery_tasks():
            self.project.save()
        find = query('Express')['results']
        assert_equal(len(find), 1)

    def test_search_node_not_name(self):
        self.project.set_title('Blue Rider-Express', self.consolidate_auth)
        with run_celery_tasks():
            self.project.save()
        find = query('Green Flyer-Slow')['results']
        assert_equal(len(find), 0)

    def test_public_parent_title(self):
        self.project.set_title('hello &amp; world', self.consolidate_auth)
        with run_celery_tasks():
            self.project.save()
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 1)
        assert_equal(docs[0]['parent_title'], 'hello & world')
        assert_true(docs[0]['parent_url'])

    def test_make_parent_private(self):
        # Make parent of component, public, then private, and verify that the
        # component still appears but doesn't link to the parent in search.
        with run_celery_tasks():
            self.project.set_privacy('private')
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 1)
        assert_false(docs[0]['parent_title'])
        assert_false(docs[0]['parent_url'])

    def test_delete_project(self):
        with run_celery_tasks():
            self.component.remove_node(self.consolidate_auth)
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 0)

        with run_celery_tasks():
            self.project.remove_node(self.consolidate_auth)
        docs = query('category:project AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    def test_change_title(self):
        title_original = self.project.title
        with run_celery_tasks():
            self.project.set_title(
                'Blue Ordinary', self.consolidate_auth, save=True
            )

        docs = query('category:project AND ' + title_original)['results']
        assert_equal(len(docs), 0)

        docs = query('category:project AND ' + self.project.title)['results']
        assert_equal(len(docs), 1)

    def test_add_tags(self):

        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

        with run_celery_tasks():
            for tag in tags:
                docs = query('tags:"{}"'.format(tag))['results']
                assert_equal(len(docs), 0)
                self.project.add_tag(tag, self.consolidate_auth, save=True)

        for tag in tags:
            docs = query('tags:"{}"'.format(tag))['results']
            assert_equal(len(docs), 1)

    def test_remove_tag(self):

        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

        for tag in tags:
            self.project.add_tag(tag, self.consolidate_auth, save=True)
            self.project.remove_tag(tag, self.consolidate_auth, save=True)
            docs = query('tags:"{}"'.format(tag))['results']
            assert_equal(len(docs), 0)

    def test_update_wiki(self):
        """Add text to a wiki page, then verify that project is found when
        searching for wiki text.

        """
        wiki_content = {
            'home': 'Hammer to fall',
            'swag': '#YOLO'
        }
        for key, value in wiki_content.items():
            docs = query(value)['results']
            assert_equal(len(docs), 0)
            with run_celery_tasks():
                WikiPage.objects.create_for_node(self.project, key, value, self.consolidate_auth)
            docs = query(value)['results']
            assert_equal(len(docs), 1)

    def test_clear_wiki(self):
        # Add wiki text to page, then delete, then verify that project is not
        # found when searching for wiki text.
        wiki_content = 'Hammer to fall'
        wp = WikiPage.objects.create_for_node(self.project, 'home', wiki_content, self.consolidate_auth)

        with run_celery_tasks():
            wp.update(self.user, '')

        docs = query(wiki_content)['results']
        assert_equal(len(docs), 0)

    def test_add_contributor(self):
        # Add a contributor, then verify that project is found when searching
        # for contributor.
        user2 = factories.UserFactory(fullname='Adam Lambert')

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)
        with run_celery_tasks():
            self.project.add_contributor(user2, save=True)

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)

    def test_remove_contributor(self):
        # Add and remove a contributor, then verify that project is not found
        # when searching for contributor.
        user2 = factories.UserFactory(fullname='Brian May')

        self.project.add_contributor(user2, save=True)
        self.project.remove_contributor(user2, self.consolidate_auth)

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)

    def test_hide_contributor(self):
        user2 = factories.UserFactory(fullname='Brian May')
        self.project.add_contributor(user2)
        with run_celery_tasks():
            self.project.set_visible(user2, False, save=True)
        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)
        with run_celery_tasks():
            self.project.set_visible(user2, True, save=True)
        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)

    def test_wrong_order_search(self):
        title_parts = self.title.split(' ')
        title_parts.reverse()
        title_search = ' '.join(title_parts)

        docs = query(title_search)['results']
        assert_equal(len(docs), 3)

    def test_tag_aggregation(self):
        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

        with run_celery_tasks():
            for tag in tags:
                self.project.add_tag(tag, self.consolidate_auth, save=True)

        docs = query(self.title)['tags']
        assert len(docs) == 3
        for doc in docs:
            assert doc['key'] in tags


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestAddContributor(OsfTestCase):
    # Tests of the search.search_contributor method

    def setUp(self):
        self.name1 = 'Roger1 Taylor1'
        self.name2 = 'John2 Deacon2'
        self.name3 = u'j\xc3\xb3ebert3 Smith3'
        self.name4 = u'B\xc3\xb3bbert4 Jones4'

        with run_celery_tasks():
            super(TestAddContributor, self).setUp()
            self.user = factories.UserFactory(fullname=self.name1)
            self.user3 = factories.UserFactory(fullname=self.name3)

    def test_unreg_users_dont_show_in_search(self):
        unreg = factories.UnregUserFactory()
        contribs = search.search_contributor(unreg.fullname)
        assert_equal(len(contribs['users']), 0)

    def test_unreg_users_do_show_on_projects(self):
        with run_celery_tasks():
            unreg = factories.UnregUserFactory(fullname='Robert Paulson')
            self.project = factories.ProjectFactory(
                title='Glamour Rock',
                creator=unreg,
                is_public=True,
            )
        results = query(unreg.fullname)['results']
        assert_equal(len(results), 1)

    def test_search_fullname(self):
        # Searching for full name yields exactly one result.
        contribs = search.search_contributor(self.name1)
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2)
        assert_equal(len(contribs['users']), 0)

    def test_search_firstname(self):
        # Searching for first name yields exactly one result.
        contribs = search.search_contributor(self.name1.split(' ')[0])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2.split(' ')[0])
        assert_equal(len(contribs['users']), 0)

    def test_search_partial(self):
        # Searching for part of first name yields exactly one
        # result.
        contribs = search.search_contributor(self.name1.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 0)

    def test_search_fullname_special_character(self):
        # Searching for a fullname with a special character yields
        # exactly one result.
        contribs = search.search_contributor(self.name3)
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name4)
        assert_equal(len(contribs['users']), 0)

    def test_search_firstname_special_charcter(self):
        # Searching for a first name with a special character yields
        # exactly one result.
        contribs = search.search_contributor(self.name3.split(' ')[0])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name4.split(' ')[0])
        assert_equal(len(contribs['users']), 0)

    def test_search_partial_special_character(self):
        # Searching for a partial name with a special character yields
        # exctly one result.
        contribs = search.search_contributor(self.name3.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name4.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 0)

    def test_search_profile(self):
        orcid = '123456'
        user = factories.UserFactory()
        user.social['orcid'] = orcid
        user.save()
        contribs = search.search_contributor(orcid)
        assert_equal(len(contribs['users']), 1)
        assert_equal(len(contribs['users'][0]['social']), 1)
        assert_equal(contribs['users'][0]['social']['orcid'], user.social_links['orcid'])


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestProjectSearchResults(OsfTestCase):
    def setUp(self):
        self.singular = 'Spanish Inquisition'
        self.plural = 'Spanish Inquisitions'
        self.possessive = 'Spanish\'s Inquisition'

        with run_celery_tasks():
            super(TestProjectSearchResults, self).setUp()
            self.user = factories.UserFactory(fullname='Doug Bogie')

            self.project_singular = factories.ProjectFactory(
                title=self.singular,
                creator=self.user,
                is_public=True,
            )

            self.project_plural = factories.ProjectFactory(
                title=self.plural,
                creator=self.user,
                is_public=True,
            )

            self.project_possessive = factories.ProjectFactory(
                title=self.possessive,
                creator=self.user,
                is_public=True,
            )

            self.project_unrelated = factories.ProjectFactory(
                title='Cardinal Richelieu',
                creator=self.user,
                is_public=True,
            )

    def test_singular_query(self):
        # Verify searching for singular term includes singular,
        # possessive and plural versions in results.
        time.sleep(1)
        results = query(self.singular)['results']
        assert_equal(len(results), 3)

    def test_plural_query(self):
        # Verify searching for singular term includes singular,
        # possessive and plural versions in results.
        results = query(self.plural)['results']
        assert_equal(len(results), 3)

    def test_possessive_query(self):
        # Verify searching for possessive term includes singular,
        # possessive and plural versions in results.
        results = query(self.possessive)['results']
        assert_equal(len(results), 3)


def job(**kwargs):
    keys = [
        'title',
        'institution',
        'department',
        'location',
        'startMonth',
        'startYear',
        'endMonth',
        'endYear',
        'ongoing',
    ]
    job = {}
    for key in keys:
        if key[-5:] == 'Month':
            job[key] = kwargs.get(key, 'December')
        elif key[-4:] == 'Year':
            job[key] = kwargs.get(key, '2000')
        else:
            job[key] = kwargs.get(key, 'test_{}'.format(key))
    return job


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestUserSearchResults(OsfTestCase):
    def setUp(self):
        with run_celery_tasks():
            super(TestUserSearchResults, self).setUp()
            self.user_one = factories.UserFactory(jobs=[job(institution='Oxford'),
                                                        job(institution='Star Fleet')],
                                                  fullname='Date Soong')

            self.user_two = factories.UserFactory(jobs=[job(institution='Grapes la Picard'),
                                                        job(institution='Star Fleet')],
                                                  fullname='Jean-Luc Picard')

            self.user_three = factories.UserFactory(jobs=[job(institution='Star Fleet'),
                                                      job(institution='Federation Medical')],
                                                    fullname='Beverly Crusher')

            self.user_four = factories.UserFactory(jobs=[job(institution='Star Fleet')],
                                                   fullname='William Riker')

            self.user_five = factories.UserFactory(jobs=[job(institution='Traveler intern'),
                                                         job(institution='Star Fleet Academy'),
                                                         job(institution='Star Fleet Intern')],
                                                   fullname='Wesley Crusher')

            for i in range(25):
                factories.UserFactory(jobs=[job()])

        self.current_starfleet = [
            self.user_three,
            self.user_four,
        ]

        self.were_starfleet = [
            self.user_one,
            self.user_two,
            self.user_three,
            self.user_four,
            self.user_five
        ]

    @unittest.skip('Cannot guarentee always passes')
    def test_current_job_first_in_results(self):
        results = query_user('Star Fleet')['results']
        result_names = [r['names']['fullname'] for r in results]
        current_starfleet_names = [u.fullname for u in self.current_starfleet]
        for name in result_names[:2]:
            assert_in(name, current_starfleet_names)

    def test_had_job_in_results(self):
        results = query_user('Star Fleet')['results']
        result_names = [r['names']['fullname'] for r in results]
        were_starfleet_names = [u.fullname for u in self.were_starfleet]
        for name in result_names:
            assert_in(name, were_starfleet_names)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchExceptions(OsfTestCase):
    # Verify that the correct exception is thrown when the connection is lost

    @classmethod
    def setUpClass(cls):
        logging.getLogger('website.project.model').setLevel(logging.CRITICAL)
        super(TestSearchExceptions, cls).setUpClass()
        if settings.SEARCH_ENGINE == 'elastic':
            cls._client = search.search_engine.CLIENT
            search.search_engine.CLIENT = None

    @classmethod
    def tearDownClass(cls):
        super(TestSearchExceptions, cls).tearDownClass()
        if settings.SEARCH_ENGINE == 'elastic':
            search.search_engine.CLIENT = cls._client

    @requires_search
    def test_connection_error(self):
        # Ensures that saving projects/users doesn't break as a result of connection errors
        self.user = factories.UserFactory(fullname='Doug Bogie')
        self.project = factories.ProjectFactory(
            title='Tom Sawyer',
            creator=self.user,
            is_public=True,
        )
        self.user.save()
        self.project.save()


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchMigration(OsfTestCase):
    # Verify that the correct indices are created/deleted during migration

    @classmethod
    def tearDownClass(cls):
        super(TestSearchMigration, cls).tearDownClass()
        search.create_index(settings.ELASTIC_INDEX)

    def setUp(self):
        super(TestSearchMigration, self).setUp()
        populate_institutions('test')
        self.es = search.search_engine.CLIENT
        search.delete_index(settings.ELASTIC_INDEX)
        search.create_index(settings.ELASTIC_INDEX)
        self.user = factories.UserFactory(fullname='David Bowie')
        self.project = factories.ProjectFactory(
            title=settings.ELASTIC_INDEX,
            creator=self.user,
            is_public=True
        )
        self.preprint = factories.PreprintFactory(
            creator=self.user
        )

    def test_first_migration_no_remove(self):
        migrate(delete=False, remove=False, index=settings.ELASTIC_INDEX, app=self.app.app)
        var = self.es.indices.get_aliases()
        assert_equal(var[settings.ELASTIC_INDEX + '_v1']['aliases'].keys()[0], settings.ELASTIC_INDEX)

    def test_multiple_migrations_no_remove(self):
        for n in range(1, 21):
            migrate(delete=False, remove=False, index=settings.ELASTIC_INDEX, app=self.app.app)
            var = self.es.indices.get_aliases()
            assert_equal(var[settings.ELASTIC_INDEX + '_v{}'.format(n)]['aliases'].keys()[0], settings.ELASTIC_INDEX)

    def test_first_migration_with_remove(self):
        migrate(delete=False, remove=True, index=settings.ELASTIC_INDEX, app=self.app.app)
        var = self.es.indices.get_aliases()
        assert_equal(var[settings.ELASTIC_INDEX + '_v1']['aliases'].keys()[0], settings.ELASTIC_INDEX)

    def test_multiple_migrations_with_remove(self):
        for n in range(1, 21, 2):
            migrate(delete=False, remove=True, index=settings.ELASTIC_INDEX, app=self.app.app)
            var = self.es.indices.get_aliases()
            assert_equal(var[settings.ELASTIC_INDEX + '_v{}'.format(n)]['aliases'].keys()[0], settings.ELASTIC_INDEX)

            migrate(delete=False, remove=True, index=settings.ELASTIC_INDEX, app=self.app.app)
            var = self.es.indices.get_aliases()
            assert_equal(var[settings.ELASTIC_INDEX + '_v{}'.format(n + 1)]['aliases'].keys()[0], settings.ELASTIC_INDEX)
            assert not var.get(settings.ELASTIC_INDEX + '_v{}'.format(n))

    def test_migration_institutions(self):
        migrate(delete=True, index=settings.ELASTIC_INDEX, app=self.app.app)
        count_query = {}
        count_query['aggregations'] = {
            'counts': {
                'terms': {
                    'field': '_type',
                }
            }
        }
        institution_bucket_found = False
        res = self.es.search(index=settings.ELASTIC_INDEX, doc_type=None, search_type='count', body=count_query)
        for bucket in res['aggregations']['counts']['buckets']:
            if bucket['key'] == u'institution':
                institution_bucket_found = True

        assert_equal(institution_bucket_found, True)

    def test_migration_collections(self):
        provider = factories.CollectionProviderFactory()
        collection_one = factories.CollectionFactory(is_public=True, provider=provider)
        collection_two = factories.CollectionFactory(is_public=True, provider=provider)
        node = factories.NodeFactory(creator=self.user, title='Ali Bomaye', is_public=True)
        collection_one.collect_object(node, self.user)
        collection_two.collect_object(node, self.user)
        assert node.is_collected

        docs = query_collections('*')['results']
        assert len(docs) == 2

        docs = query_collections('Bomaye')['results']
        assert len(docs) == 2

        count_query = {}
        count_query['aggregations'] = {
            'counts': {
                'terms': {
                    'field': '_type',
                }
            }
        }

        migrate(delete=True, index=settings.ELASTIC_INDEX, app=self.app.app)

        docs = query_collections('*')['results']
        assert len(docs) == 2

        docs = query_collections('Bomaye')['results']
        assert len(docs) == 2

        res = self.es.search(index=settings.ELASTIC_INDEX, doc_type='collectionSubmission', search_type='count', body=count_query)
        assert res['hits']['total'] == 2

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchFiles(OsfTestCase):

    def setUp(self):
        super(TestSearchFiles, self).setUp()
        self.node = factories.ProjectFactory(is_public=True, title='Otis')
        self.osf_storage = self.node.get_addon('osfstorage')
        self.root = self.osf_storage.get_root()

    def test_search_file(self):
        self.root.append_file('Shake.wav')
        find = query_file('Shake.wav')['results']
        assert_equal(len(find), 1)

    def test_search_file_name_without_separator(self):
        self.root.append_file('Shake.wav')
        find = query_file('Shake')['results']
        assert_equal(len(find), 1)

    def test_delete_file(self):
        file_ = self.root.append_file('I\'ve Got Dreams To Remember.wav')
        find = query_file('I\'ve Got Dreams To Remember.wav')['results']
        assert_equal(len(find), 1)
        file_.delete()
        find = query_file('I\'ve Got Dreams To Remember.wav')['results']
        assert_equal(len(find), 0)

    def test_add_tag(self):
        file_ = self.root.append_file('That\'s How Strong My Love Is.mp3')
        tag = Tag(name='Redding')
        tag.save()
        file_.tags.add(tag)
        file_.save()
        find = query_tag_file('Redding')['results']
        assert_equal(len(find), 1)

    def test_remove_tag(self):
        file_ = self.root.append_file('I\'ve Been Loving You Too Long.mp3')
        tag = Tag(name='Blue')
        tag.save()
        file_.tags.add(tag)
        file_.save()
        find = query_tag_file('Blue')['results']
        assert_equal(len(find), 1)
        file_.tags.remove(tag)
        file_.save()
        find = query_tag_file('Blue')['results']
        assert_equal(len(find), 0)

    def test_make_node_private(self):
        self.root.append_file('Change_Gonna_Come.wav')
        find = query_file('Change_Gonna_Come.wav')['results']
        assert_equal(len(find), 1)
        self.node.is_public = False
        with run_celery_tasks():
            self.node.save()
        find = query_file('Change_Gonna_Come.wav')['results']
        assert_equal(len(find), 0)

    def test_make_private_node_public(self):
        self.node.is_public = False
        self.node.save()
        self.root.append_file('Try a Little Tenderness.flac')
        find = query_file('Try a Little Tenderness.flac')['results']
        assert_equal(len(find), 0)
        self.node.is_public = True
        with run_celery_tasks():
            self.node.save()
        find = query_file('Try a Little Tenderness.flac')['results']
        assert_equal(len(find), 1)

    def test_delete_node(self):
        node = factories.ProjectFactory(is_public=True, title='The Soul Album')
        osf_storage = node.get_addon('osfstorage')
        root = osf_storage.get_root()
        root.append_file('The Dock of the Bay.mp3')
        find = query_file('The Dock of the Bay.mp3')['results']
        assert_equal(len(find), 1)
        node.is_deleted = True
        with run_celery_tasks():
            node.save()
        find = query_file('The Dock of the Bay.mp3')['results']
        assert_equal(len(find), 0)

    def test_file_download_url_guid(self):
        file_ = self.root.append_file('Timber.mp3')
        file_guid = file_.get_guid(create=True)
        file_.save()
        find = query_file('Timber.mp3')['results']
        assert_equal(find[0]['guid_url'], '/' + file_guid._id + '/')

    def test_file_download_url_no_guid(self):
        file_ = self.root.append_file('Timber.mp3')
        path = file_.path
        deep_url = '/' + file_.target._id + '/files/osfstorage' + path + '/'
        find = query_file('Timber.mp3')['results']
        assert_not_equal(file_.path, '')
        assert_equal(file_.path, path)
        assert_equal(find[0]['guid_url'], None)
        assert_equal(find[0]['deep_url'], deep_url)

    @pytest.mark.enable_quickfiles_creation
    def test_quickfiles_files_appear_in_search(self):
        quickfiles = QuickFilesNode.objects.get(creator=self.node.creator)
        quickfiles_osf_storage = quickfiles.get_addon('osfstorage')
        quickfiles_root = quickfiles_osf_storage.get_root()

        quickfiles_root.append_file('GreenLight.mp3')
        find = query_file('GreenLight.mp3')['results']
        assert_equal(len(find), 1)
        assert find[0]['node_url'] == '/{}/quickfiles/'.format(quickfiles.creator._id)

    @pytest.mark.enable_quickfiles_creation
    def test_qatest_quickfiles_files_not_appear_in_search(self):
        quickfiles = QuickFilesNode.objects.get(creator=self.node.creator)
        quickfiles_osf_storage = quickfiles.get_addon('osfstorage')
        quickfiles_root = quickfiles_osf_storage.get_root()

        file = quickfiles_root.append_file('GreenLight.mp3')
        tag = Tag(name='qatest')
        tag.save()
        file.tags.add(tag)
        file.save()

        find = query_file('GreenLight.mp3')['results']
        assert_equal(len(find), 0)

    @pytest.mark.enable_quickfiles_creation
    def test_quickfiles_spam_user_files_do_not_appear_in_search(self):
        quickfiles = QuickFilesNode.objects.get(creator=self.node.creator)
        quickfiles_osf_storage = quickfiles.get_addon('osfstorage')
        quickfiles_root = quickfiles_osf_storage.get_root()
        quickfiles_root.append_file('GreenLight.mp3')

        self.node.creator.disable_account()
        self.node.creator.add_system_tag('spam_confirmed')
        self.node.creator.save()

        find = query_file('GreenLight.mp3')['results']
        assert_equal(len(find), 0)
