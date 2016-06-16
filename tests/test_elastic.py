# -*- coding: utf-8 -*-
import time
import unittest
import logging
import functools

from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
from modularodm import Q

from framework.auth.core import Auth
from website import settings
import website.search.search as search
from website.search import elastic_search
from website.search.util import build_query
from website.search_migration.migrate import migrate
from website.models import Retraction, NodeLicense, Tag

from tests.base import OsfTestCase
from tests.test_features import requires_search
from tests.factories import (
    UserFactory, ProjectFactory, NodeFactory,
    UnregUserFactory, UnconfirmedUserFactory,
    RegistrationFactory,
    NodeLicenseRecordFactory
)
from tests.utils import mock_archive

TEST_INDEX = 'test'

@requires_search
class SearchTestCase(OsfTestCase):

    def tearDown(self):
        super(SearchTestCase, self).tearDown()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
    def setUp(self):
        super(SearchTestCase, self).setUp()
        elastic_search.INDEX = TEST_INDEX
        settings.ELASTIC_INDEX = TEST_INDEX
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)


def query(term):
    results = search.search(build_query(term), index=elastic_search.INDEX)
    return results


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


@requires_search
class TestUserUpdate(SearchTestCase):

    def setUp(self):
        super(TestUserUpdate, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
        self.user = UserFactory(fullname='David Bowie')

    def test_new_user(self):
        # Verify that user has been added to Elastic Search
        docs = query_user(self.user.fullname)['results']
        assert_equal(len(docs), 1)

    def test_new_user_unconfirmed(self):
        user = UnconfirmedUserFactory()
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
        user = UserFactory(fullname='Barry Mitchell')
        fullname_original = user.fullname
        user.fullname = user.fullname[::-1]
        user.save()

        docs_original = query_user(fullname_original)['results']
        assert_equal(len(docs_original), 0)

        docs_current = query_user(user.fullname)['results']
        assert_equal(len(docs_current), 1)

    def test_disabled_user(self):
        # Test that disabled users are not in search index

        user = UserFactory(fullname='Bettie Page')
        user.save()

        # Ensure user is in search index
        assert_equal(len(query_user(user.fullname)['results']), 1)

        # Disable the user
        user.is_disabled = True
        user.save()

        # Ensure user is not in search index
        assert_equal(len(query_user(user.fullname)['results']), 0)

    def test_merged_user(self):
        user = UserFactory(fullname='Annie Lennox')
        merged_user = UserFactory(fullname='Lisa Stansfield')
        user.save()
        merged_user.save()
        assert_equal(len(query_user(user.fullname)['results']), 1)
        assert_equal(len(query_user(merged_user.fullname)['results']), 1)

        user.merge_user(merged_user)

        assert_equal(len(query_user(user.fullname)['results']), 1)
        assert_equal(len(query_user(merged_user.fullname)['results']), 0)

    def test_employment(self):
        user = UserFactory(fullname='Helga Finn')
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
        user = UserFactory(fullname='Henry Johnson')
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
        user = UserFactory(fullname=names[0])
        user.given_name = names[1]
        user.middle_names = names[2]
        user.family_name = names[3]
        user.suffix = names[4]
        user.save()
        docs = [query_user(name)['results'] for name in names]
        assert_equal(sum(map(len, docs)), len(docs))  # 1 result each
        assert_true(all([user._id == doc[0]['id'] for doc in docs]))


@requires_search
class TestProject(SearchTestCase):

    def setUp(self):
        super(TestProject, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
        self.user = UserFactory(fullname='John Deacon')
        self.project = ProjectFactory(title='Red Special', creator=self.user)

    def test_new_project_private(self):
        # Verify that a private project is not present in Elastic Search.
        docs = query(self.project.title)['results']
        assert_equal(len(docs), 0)

    def test_make_public(self):
        # Make project public, and verify that it is present in Elastic
        # Search.
        self.project.set_privacy('public')
        docs = query(self.project.title)['results']
        assert_equal(len(docs), 1)


@requires_search
class TestNodeSearch(SearchTestCase):

    def setUp(self):
        super(TestNodeSearch, self).setUp()
        self.node = ProjectFactory(is_public=True, title='node')
        self.public_child = ProjectFactory(parent=self.node, is_public=True, title='public_child')
        self.private_child = ProjectFactory(parent=self.node, title='private_child')
        self.public_subchild = ProjectFactory(parent=self.private_child, is_public=True)
        self.node.node_license = NodeLicenseRecordFactory()
        self.node.save()

        self.query = 'category:project & category:component'

    @retry_assertion()
    def test_node_license_added_to_search(self):
        docs = query(self.query)['results']
        node = [d for d in docs if d['title'] == self.node.title][0]
        assert_in('license', node)
        assert_equal(node['license']['id'], self.node.node_license.id)

    @unittest.skip("Elasticsearch latency seems to be causing theses tests to fail randomly.")
    @retry_assertion(retries=10)
    def test_node_license_propogates_to_children(self):
        docs = query(self.query)['results']
        child = [d for d in docs if d['title'] == self.public_child.title][0]
        assert_in('license', child)
        assert_equal(child['license'].get('id'), self.node.node_license.id)
        child = [d for d in docs if d['title'] == self.public_subchild.title][0]
        assert_in('license', child)
        assert_equal(child['license'].get('id'), self.node.node_license.id)

    @unittest.skip("Elasticsearch latency seems to be causing theses tests to fail randomly.")
    @retry_assertion(retries=10)
    def test_node_license_updates_correctly(self):
        other_license = NodeLicense.find_one(
            Q('name', 'eq', 'MIT License')
        )
        new_license = NodeLicenseRecordFactory(node_license=other_license)
        self.node.node_license = new_license
        self.node.save()
        docs = query(self.query)['results']
        for doc in docs:
            assert_equal(doc['license'].get('id'), new_license.id)

@requires_search
class TestRegistrationRetractions(SearchTestCase):

    def setUp(self):
        super(TestRegistrationRetractions, self).setUp()
        self.user = UserFactory(usename='Doug Bogie')
        self.title = 'Red Special'
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(
            title=self.title,
            creator=self.user,
            is_public=True,
        )
        with mock_archive(
                self.project,
                autocomplete=True,
                autoapprove=True
        ) as registration:
            self.registration = registration

    def test_retraction_is_not_searchable(self):
        self.registration.retract_registration(self.user)
        self.registration.retraction.state = Retraction.APPROVED
        self.registration.retraction.save()
        self.registration.save()
        self.registration.retraction._on_complete(self.user)
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    @mock.patch('website.project.model.Node.archiving', mock.PropertyMock(return_value=False))
    def test_pending_retraction_wiki_content_is_searchable(self):
        # Add unique string to wiki
        wiki_content = {'home': 'public retraction test'}
        for key, value in wiki_content.items():
            docs = query(value)['results']
            assert_equal(len(docs), 0)
            self.registration.update_node_wiki(
                key, value, self.consolidate_auth,
            )
            # Query and ensure unique string shows up
            docs = query(value)['results']
            assert_equal(len(docs), 1)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

        # Retract registration
        self.registration.retract_registration(self.user, '')
        self.registration.save()
        self.registration.reload()

        # Query and ensure unique string in wiki doesn't show up
        docs = query('category:registration AND "{}"'.format(wiki_content['home']))['results']
        assert_equal(len(docs), 1)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

    @mock.patch('website.project.model.Node.archiving', mock.PropertyMock(return_value=False))
    def test_retraction_wiki_content_is_not_searchable(self):
        # Add unique string to wiki
        wiki_content = {'home': 'public retraction test'}
        for key, value in wiki_content.items():
            docs = query(value)['results']
            assert_equal(len(docs), 0)
            self.registration.update_node_wiki(
                key, value, self.consolidate_auth,
            )
            # Query and ensure unique string shows up
            docs = query(value)['results']
            assert_equal(len(docs), 1)

        # Query and ensure registration does show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 1)

        # Retract registration
        self.registration.retract_registration(self.user, '')
        self.registration.retraction.state = Retraction.APPROVED
        self.registration.retraction.save()
        self.registration.save()
        self.registration.update_search()

        # Query and ensure unique string in wiki doesn't show up
        docs = query('category:registration AND "{}"'.format(wiki_content['home']))['results']
        assert_equal(len(docs), 0)

        # Query and ensure registration does not show up
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 0)


@requires_search
class TestPublicNodes(SearchTestCase):

    def setUp(self):
        super(TestPublicNodes, self).setUp()
        self.user = UserFactory(usename='Doug Bogie')
        self.title = 'Red Special'
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(
            title=self.title,
            creator=self.user,
            is_public=True,
        )
        self.component = NodeFactory(
            parent=self.project,
            title=self.title,
            creator=self.user,
            is_public=True
        )
        self.registration = ProjectFactory(
            title=self.title,
            creator=self.user,
            is_public=True,
            is_registration=True
        )

    def test_make_private(self):
        # Make project public, then private, and verify that it is not present
        # in search.
        self.project.set_privacy('private')
        docs = query('category:project AND ' + self.title)['results']
        assert_equal(len(docs), 0)

        self.component.set_privacy('private')
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    def test_public_parent_title(self):
        self.project.set_title('hello &amp; world', self.consolidate_auth)
        self.project.save()
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 1)
        assert_equal(docs[0]['parent_title'], 'hello & world')
        assert_true(docs[0]['parent_url'])

    def test_make_parent_private(self):
        # Make parent of component, public, then private, and verify that the
        # component still appears but doesn't link to the parent in search.
        self.project.set_privacy('private')
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 1)
        assert_equal(docs[0]['parent_title'], '-- private project --')
        assert_false(docs[0]['parent_url'])

    def test_delete_project(self):
        self.component.remove_node(self.consolidate_auth)
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 0)

        self.project.remove_node(self.consolidate_auth)
        docs = query('category:project AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    def test_change_title(self):
        title_original = self.project.title
        self.project.set_title(
            'Blue Ordinary', self.consolidate_auth, save=True)

        docs = query('category:project AND ' + title_original)['results']
        assert_equal(len(docs), 0)

        docs = query('category:project AND ' + self.project.title)['results']
        assert_equal(len(docs), 1)

    def test_add_tags(self):

        tags = ['stonecoldcrazy', 'just a poor boy', 'from-a-poor-family']

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
            self.project.update_node_wiki(
                key, value, self.consolidate_auth,
            )
            docs = query(value)['results']
            assert_equal(len(docs), 1)

    def test_clear_wiki(self):
        # Add wiki text to page, then delete, then verify that project is not
        # found when searching for wiki text.
        wiki_content = 'Hammer to fall'
        self.project.update_node_wiki(
            'home', wiki_content, self.consolidate_auth,
        )
        self.project.update_node_wiki('home', '', self.consolidate_auth)

        docs = query(wiki_content)['results']
        assert_equal(len(docs), 0)

    def test_add_contributor(self):
        # Add a contributor, then verify that project is found when searching
        # for contributor.
        user2 = UserFactory(fullname='Adam Lambert')

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)

        self.project.add_contributor(user2, save=True)

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)

    def test_remove_contributor(self):
        # Add and remove a contributor, then verify that project is not found
        # when searching for contributor.
        user2 = UserFactory(fullname='Brian May')

        self.project.add_contributor(user2, save=True)
        self.project.remove_contributor(user2, self.consolidate_auth)

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)

    def test_hide_contributor(self):
        user2 = UserFactory(fullname='Brian May')
        self.project.add_contributor(user2)
        self.project.set_visible(user2, False, save=True)
        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)
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

        for tag in tags:
            self.project.add_tag(tag, self.consolidate_auth, save=True)

        docs = query(self.title)['tags']
        assert len(docs) == 3
        for doc in docs:
            assert doc['key'] in tags


@requires_search
class TestAddContributor(SearchTestCase):
    # Tests of the search.search_contributor method

    def setUp(self):
        super(TestAddContributor, self).setUp()
        self.name1 = 'Roger1 Taylor1'
        self.name2 = 'John2 Deacon2'
        self.name3 = u'j\xc3\xb3ebert3 Smith3'
        self.name4 = u'B\xc3\xb3bbert4 Jones4'
        self.user = UserFactory(fullname=self.name1)
        self.user3 = UserFactory(fullname=self.name3)

    def test_unreg_users_dont_show_in_search(self):
        unreg = UnregUserFactory()
        contribs = search.search_contributor(unreg.fullname)
        assert_equal(len(contribs['users']), 0)


    def test_unreg_users_do_show_on_projects(self):
        unreg = UnregUserFactory(fullname='Robert Paulson')
        self.project = ProjectFactory(
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

@requires_search
class TestProjectSearchResults(SearchTestCase):
    def setUp(self):
        super(TestProjectSearchResults, self).setUp()
        self.user = UserFactory(usename='Doug Bogie')

        self.singular = 'Spanish Inquisition'
        self.plural = 'Spanish Inquisitions'
        self.possessive = 'Spanish\'s Inquisition'

        self.project_singular = ProjectFactory(
            title=self.singular,
            creator=self.user,
            is_public=True,
        )

        self.project_plural = ProjectFactory(
            title=self.plural,
            creator=self.user,
            is_public=True,
        )

        self.project_possessive = ProjectFactory(
            title=self.possessive,
            creator=self.user,
            is_public=True,
        )

        self.project_unrelated = ProjectFactory(
            title='Cardinal Richelieu',
            creator=self.user,
            is_public=True,
        )

    def test_singular_query(self):
        # Verify searching for singular term includes singular,
        # possessive and plural versions in results.
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


class TestUserSearchResults(SearchTestCase):
    def setUp(self):
        super(TestUserSearchResults, self).setUp()
        self.user_one = UserFactory(jobs=[job(institution='Oxford'),
                                          job(institution='Star Fleet')],
                                    fullname='Date Soong')

        self.user_two = UserFactory(jobs=[job(institution='Grapes la Picard'),
                                          job(institution='Star Fleet')],
                                    fullname='Jean-Luc Picard')

        self.user_three = UserFactory(jobs=[job(institution='Star Fleet'),
                                            job(institution='Federation Medical')],
                                      fullname='Beverly Crusher')

        self.user_four = UserFactory(jobs=[job(institution='Star Fleet')],
                                     fullname='William Riker')

        self.user_five = UserFactory(jobs=[job(institution='Traveler intern'),
                                           job(institution='Star Fleet Academy'),
                                           job(institution='Star Fleet Intern')],
                                     fullname='Wesley Crusher')

        for i in range(25):
            UserFactory(jobs=[job()])

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


class TestSearchExceptions(OsfTestCase):
    # Verify that the correct exception is thrown when the connection is lost

    @classmethod
    def setUpClass(cls):
        logging.getLogger('website.project.model').setLevel(logging.CRITICAL)
        super(TestSearchExceptions, cls).setUpClass()
        if settings.SEARCH_ENGINE == 'elastic':
            cls._es = search.search_engine.es
            search.search_engine.es = None

    @classmethod
    def tearDownClass(cls):
        super(TestSearchExceptions, cls).tearDownClass()
        if settings.SEARCH_ENGINE == 'elastic':
            search.search_engine.es = cls._es

    def test_connection_error(self):
        # Ensures that saving projects/users doesn't break as a result of connection errors
        self.user = UserFactory(usename='Doug Bogie')
        self.project = ProjectFactory(
            title="Tom Sawyer",
            creator=self.user,
            is_public=True,
        )
        self.user.save()
        self.project.save()


class TestSearchMigration(SearchTestCase):
    # Verify that the correct indices are created/deleted during migration

    @classmethod
    def tearDownClass(cls):
        super(TestSearchMigration, cls).tearDownClass()
        search.create_index(settings.ELASTIC_INDEX)

    def setUp(self):
        super(TestSearchMigration, self).setUp()
        self.es = search.search_engine.es
        search.delete_index(settings.ELASTIC_INDEX)
        search.create_index(settings.ELASTIC_INDEX)
        self.user = UserFactory(fullname='David Bowie')
        self.project = ProjectFactory(
            title=settings.ELASTIC_INDEX,
            creator=self.user,
            is_public=True
        )

    def test_first_migration_no_delete(self):
        migrate(delete=False, index=settings.ELASTIC_INDEX, app=self.app.app)
        var = self.es.indices.get_aliases()
        assert_equal(var[settings.ELASTIC_INDEX + '_v1']['aliases'].keys()[0], settings.ELASTIC_INDEX)

    def test_multiple_migrations_no_delete(self):
        for n in xrange(1, 21):
            migrate(delete=False, index=settings.ELASTIC_INDEX, app=self.app.app)
            var = self.es.indices.get_aliases()
            assert_equal(var[settings.ELASTIC_INDEX + '_v{}'.format(n)]['aliases'].keys()[0], settings.ELASTIC_INDEX)

    def test_first_migration_with_delete(self):
        migrate(delete=True, index=settings.ELASTIC_INDEX, app=self.app.app)
        var = self.es.indices.get_aliases()
        assert_equal(var[settings.ELASTIC_INDEX + '_v1']['aliases'].keys()[0], settings.ELASTIC_INDEX)

    def test_multiple_migrations_with_delete(self):
        for n in xrange(1, 21, 2):
            migrate(delete=True, index=settings.ELASTIC_INDEX, app=self.app.app)
            var = self.es.indices.get_aliases()
            assert_equal(var[settings.ELASTIC_INDEX + '_v{}'.format(n)]['aliases'].keys()[0], settings.ELASTIC_INDEX)

            migrate(delete=True, index=settings.ELASTIC_INDEX, app=self.app.app)
            var = self.es.indices.get_aliases()
            assert_equal(var[settings.ELASTIC_INDEX + '_v{}'.format(n + 1)]['aliases'].keys()[0], settings.ELASTIC_INDEX)
            assert not var.get(settings.ELASTIC_INDEX + '_v{}'.format(n))

class TestSearchFiles(SearchTestCase):

    def setUp(self):
        super(TestSearchFiles, self).setUp()
        self.node = ProjectFactory(is_public=True, title='Otis')
        self.osf_storage = self.node.get_addon('osfstorage')
        self.root = self.osf_storage.get_root()

    def test_search_file(self):
        self.root.append_file('Shake.wav')
        find = query_file('Shake.wav')['results']
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
        tag = Tag(_id='Redding')
        tag.save()
        file_.tags.append(tag)
        file_.save()
        find = query_tag_file('Redding')['results']
        assert_equal(len(find), 1)

    def test_remove_tag(self):
        file_ = self.root.append_file('I\'ve Been Loving You Too Long.mp3')
        tag = Tag(_id='Blue')
        tag.save()
        file_.tags.append(tag)
        file_.save()
        find = query_tag_file('Blue')['results']
        assert_equal(len(find), 1)
        file_.tags.remove('Blue')
        file_.save()
        find = query_tag_file('Blue')['results']
        assert_equal(len(find), 0)

    def test_make_node_private(self):
        file_ = self.root.append_file('Change_Gonna_Come.wav')
        find = query_file('Change_Gonna_Come.wav')['results']
        assert_equal(len(find), 1)
        self.node.is_public = False
        self.node.save()
        find = query_file('Change_Gonna_Come.wav')['results']
        assert_equal(len(find), 0)

    def test_make_private_node_public(self):
        self.node.is_public = False
        self.node.save()
        file_ = self.root.append_file('Try a Little Tenderness.flac')
        find = query_file('Try a Little Tenderness.flac')['results']
        assert_equal(len(find), 0)
        self.node.is_public = True
        self.node.save()
        find = query_file('Try a Little Tenderness.flac')['results']
        assert_equal(len(find), 1)

    def test_delete_node(self):
        node = ProjectFactory(is_public=True, title='The Soul Album')
        osf_storage = node.get_addon('osfstorage')
        root = osf_storage.get_root()
        root.append_file('The Dock of the Bay.mp3')
        find = query_file('The Dock of the Bay.mp3')['results']
        assert_equal(len(find), 1)
        node.is_deleted = True
        node.save()
        find = query_file('The Dock of the Bay.mp3')['results']
        assert_equal(len(find), 0)
