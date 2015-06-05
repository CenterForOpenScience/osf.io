import unittest
import logging

from nose.tools import *  # flake8: noqa (PEP8 asserts)

from framework.auth.core import Auth
from website import settings
import website.search.search as search
from website.search import elastic_search
from website.search.util import build_query
from website.search_migration.migrate import migrate

from tests.base import OsfTestCase
from tests.test_features import requires_search
from tests.factories import (
    UserFactory, ProjectFactory, NodeFactory,
    UnregUserFactory, UnconfirmedUserFactory
)

@requires_search
class SearchTestCase(OsfTestCase):

    def tearDown(self):
        super(SearchTestCase, self).tearDown()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
    def setUp(self):
        super(SearchTestCase, self).setUp()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)


def query(term):
    results = search.search(build_query(term), index=elastic_search.INDEX)
    return results


def query_user(name):
    term = 'category:user AND "{}"'.format(name)
    return query(term)


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
        """Add a user, change her name, and verify that only the new name is
        found in search.

        """
        user = UserFactory(fullname='Barry Mitchell')
        fullname_original = user.fullname
        user.fullname = user.fullname[::-1]
        user.save()

        docs_original = query_user(fullname_original)['results']
        assert_equal(len(docs_original), 0)

        docs_current = query_user(user.fullname)['results']
        assert_equal(len(docs_current), 1)

    def test_disabled_user(self):
        """Test that disabled users are not in search index"""

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
        """Verify that a private project is not present in Elastic Search.
        """
        docs = query(self.project.title)['results']
        assert_equal(len(docs), 0)

    def test_make_public(self):
        """Make project public, and verify that it is present in Elastic
        Search.
        """
        self.project.set_privacy('public')
        docs = query(self.project.title)['results']
        assert_equal(len(docs), 1)


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
        """Make project public, then private, and verify that it is not present
        in search.
        """
        self.project.set_privacy('private')
        docs = query('category:project AND ' + self.title)['results']
        assert_equal(len(docs), 0)

        self.component.set_privacy('private')
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 0)
        self.registration.set_privacy('private')
        docs = query('category:registration AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    def test_public_parent_title(self):
        self.project.set_title('hello &amp; world', self.consolidate_auth)
        self.project.save()
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 1)
        assert_equal(docs[0]['parent_title'], 'hello & world')
        assert_true(docs[0]['parent_url'])

    def test_make_parent_private(self):
        """Make parent of component, public, then private, and verify that the
        component still appears but doesn't link to the parent in search.
        """
        self.project.set_privacy('private')
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 1)
        assert_equal(docs[0]['parent_title'], '-- private project --')
        assert_false(docs[0]['parent_url'])

    def test_delete_project(self):
        """

        """
        self.component.remove_node(self.consolidate_auth)
        docs = query('category:component AND ' + self.title)['results']
        assert_equal(len(docs), 0)

        self.project.remove_node(self.consolidate_auth)
        docs = query('category:project AND ' + self.title)['results']
        assert_equal(len(docs), 0)

    def test_change_title(self):
        """

        """
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
        """Add wiki text to page, then delete, then verify that project is not
        found when searching for wiki text.

        """
        wiki_content = 'Hammer to fall'
        self.project.update_node_wiki(
            'home', wiki_content, self.consolidate_auth,
        )
        self.project.update_node_wiki('home', '', self.consolidate_auth)

        docs = query(wiki_content)['results']
        assert_equal(len(docs), 0)

    def test_add_contributor(self):
        """Add a contributor, then verify that project is found when searching
        for contributor.

        """
        user2 = UserFactory(fullname='Adam Lambert')

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 0)

        self.project.add_contributor(user2, save=True)

        docs = query('category:project AND "{}"'.format(user2.fullname))['results']
        assert_equal(len(docs), 1)

    def test_remove_contributor(self):
        """Add and remove a contributor, then verify that project is not found
        when searching for contributor.

        """
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
    """Tests of the search.search_contributor method

    """

    def setUp(self):
        super(TestAddContributor, self).setUp()
        self.name1 = 'Roger1 Taylor1'
        self.name2 = 'John2 Deacon2'
        self.user = UserFactory(fullname=self.name1)

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
        """Verify that searching for full name yields exactly one result.

        """
        contribs = search.search_contributor(self.name1)
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2)
        assert_equal(len(contribs['users']), 0)

    def test_search_firstname(self):
        """Verify that searching for first name yields exactly one result.

        """
        contribs = search.search_contributor(self.name1.split(' ')[0])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2.split(' ')[0])
        assert_equal(len(contribs['users']), 0)

    def test_search_partial(self):
        """Verify that searching for part of first name yields exactly one
        result.

        """
        contribs = search.search_contributor(self.name1.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 1)

        contribs = search.search_contributor(self.name2.split(' ')[0][:-1])
        assert_equal(len(contribs['users']), 0)


class TestSearchExceptions(OsfTestCase):
    """
    Verify that the correct exception is thrown when the connection is lost
    """

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
