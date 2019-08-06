import pytest
import mock

from nose.tools import *  # noqa PEP8 asserts

from website import settings
import website.search.search as search
from website.search_migration.migrate import migrate
from website.search.util import build_query

from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory, InstitutionFactory, ProjectFactory
from osf_tests.test_elastic_search import retry_assertion

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestContributorSearch(OsfTestCase):

    def setUp(self):
        super(TestContributorSearch, self).setUp()

        self.firstname = 'jane'
        self.fullname1 = self.firstname + ' 1'
        self.fullname2 = self.firstname + ' 2'
        self.fullname3 = self.firstname + ' 3'
        self.dummy1_fullname = self.firstname + ' dummy1'
        self.dummy2_fullname = self.firstname + ' dummy2'
        self.dummy3_fullname = self.firstname + ' dummy3'
        self.dummy4_fullname = self.firstname + ' dummy4'

        self.inst1 = inst1 = InstitutionFactory()
        self.inst2 = inst2 = InstitutionFactory()

        def create_user(name, insts):
            user = AuthUserFactory(fullname=name)
            for inst in insts:
                user.affiliated_institutions.add(inst)
            user.middle_names = 'd'  # WORKAROUND: dirty field for call of OSFUser.update_search. see https://github.com/romgar/django-dirtyfields/issues/73 and https://django-dirtyfields.readthedocs.io/en/develop/#checking-many-to-many-fields for details.
            user.save()
            return user

        self.user1 = create_user(self.fullname1, (self.inst1,))
        self.user2 = create_user(self.fullname2, (self.inst1, self.inst2))
        self.user3 = create_user(self.fullname3, ())

        create_user(self.dummy1_fullname, (self.inst1,))
        create_user(self.dummy2_fullname, (self.inst1,))
        create_user(self.dummy3_fullname, (self.inst2,))
        create_user(self.dummy4_fullname, (self.inst2,))

        self.inst1_users = [u.fullname for u in inst1.osfuser_set.all()]
        self.inst2_users = [u.fullname for u in inst2.osfuser_set.all()]

        # dummy_project
        ProjectFactory(creator=self.user1, is_public=False)

    # migrate() may not update elasticsearch-data immediately.
    @retry_assertion(retries=10)
    def test_search_contributors_from_my_institutions(self):
        def search_contribs(current_user):
            return search.search_contributor(
                self.firstname,
                current_user=current_user
            )

        # one institution
        contribs = search_contribs(self.user1)
        assert_equal(set([u['fullname'] for u in contribs['users']]),
                     set(self.inst1_users))

        # two institutions
        contribs = search_contribs(self.user2)
        assert_equal(set([u['fullname'] for u in contribs['users']]),
                     set(self.inst1_users) | set(self.inst2_users))

        # independent (no institution) -> from all institutions
        contribs = search_contribs(self.user3)
        assert_equal(len(contribs['users']), 7)

    def test_search_contributors_from_my_institutions_after_rebuild_search(self):
        # after migrate (= rebuild_search)
        migrate(delete=False, remove=False,
                index=settings.ELASTIC_INDEX, app=self.app.app)
        self.test_search_contributors_from_my_institutions()

    def test_search_contributors_by_guid(self):
        contribs = search.search_contributor(
            self.user2._id,
            current_user=self.user1
        )
        assert_equal(set([u['fullname'] for u in contribs['users']]),
                     set([self.user2.fullname]))


class TestEscape(OsfTestCase):

    def test_es_escape(self):
        import string
        from website.search.util import es_escape

        # see https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#_reserved_characters
        assert_equal(es_escape('+-=&|!(){}[]^"~*?:/'),
                     '\+\-\=\&\|\!\(\)\{\}\[\]\^\\\"\~\*\?\:\/')
        assert_equal(es_escape('"'), '\\\"')   # " -> \"
        assert_equal(es_escape('\\'), '\\\\')  # \ -> \\
        assert_equal(es_escape('><'), '  ')  # whitespace
        assert_equal(es_escape("'"), "'")  # not escaped

        other_punctuation = '#$%,.;@_`'
        assert_equal(es_escape(other_punctuation), other_punctuation)

        assert_equal(es_escape(string.letters), string.letters)
        assert_equal(es_escape(string.octdigits), string.octdigits)
        assert_equal(es_escape(string.whitespace), string.whitespace)

        hiragana = ''.join([unichr(i) for i in range(12353, 12436)])
        assert_equal(es_escape(hiragana), hiragana)

        katakana = ''.join([unichr(i) for i in range(12449, 12533)])
        assert_equal(es_escape(katakana), katakana)

        zenkaku_hankaku = ''.join([unichr(i) for i in range(65281, 65440)])
        assert_equal(es_escape(zenkaku_hankaku), zenkaku_hankaku)


# see ./osf_tests/test_elastic_search.py
@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchMigrationNormalizedField(OsfTestCase):

    @classmethod
    def tearDownClass(cls):
        super(TestSearchMigrationNormalizedField, cls).tearDownClass()
        search.create_index(settings.ELASTIC_INDEX)

    def setUp(self):
        super(TestSearchMigrationNormalizedField, self).setUp()
        self.es = search.search_engine.CLIENT
        search.delete_index(settings.ELASTIC_INDEX)
        search.create_index(settings.ELASTIC_INDEX)

        self.inst1 = InstitutionFactory()

        self.testname = u'\u00c3\u00c3\u00c3'
        self.testname_normalized = 'AAA'

        self.user1 = AuthUserFactory()
        self.user1.affiliated_institutions.add(self.inst1)
        self.user1.fullname = self.testname
        self.user1.save()

        self.user2 = AuthUserFactory()
        self.user2.affiliated_institutions.add(self.inst1)
        self.user2.given_name = self.testname
        self.user2.save()

        self.user3 = AuthUserFactory()
        self.user3.affiliated_institutions.add(self.inst1)
        self.user3.family_name = self.testname
        self.user3.save()

        self.user4 = AuthUserFactory()
        self.user4.affiliated_institutions.add(self.inst1)
        self.user4.middle_names = self.testname
        self.user4.save()

        self.user5 = AuthUserFactory()
        self.user5.affiliated_institutions.add(self.inst1)
        self.user5.suffix = self.testname
        self.user5.save()

        self.users = (self.user1, self.user2, self.user3,
                      self.user4, self.user5)

        self.project = ProjectFactory(
            title=self.testname,
            creator=self.user1,
            is_public=True
        )

        self.TOTAL_USERS = len(self.users)
        self.TOTAL_PROJECTS = 1

    # migrate() may not update elasticsearch-data immediately.
    @retry_assertion(retries=10)
    def search_contrib(self, expect_num):
        contribs = search.search_contributor(
            self.testname_normalized,
            current_user=self.user1
        )
        assert_equal(len(contribs['users']), expect_num)

    # migrate() may not update elasticsearch-data immediately.
    @retry_assertion(retries=10)
    def search_project(self, expect_num):
        r = search.search(build_query(self.testname_normalized),
                          doc_type='project',
                          index=settings.ELASTIC_INDEX, raw=False)
        assert_equal(len(r['results']), expect_num)

    def test_rebuild_search_check_normalized(self):
        self.search_contrib(self.TOTAL_USERS)
        self.search_project(self.TOTAL_PROJECTS)

        # after update_search()
        for u in self.users:
            u.update_search()
        self.search_contrib(self.TOTAL_USERS)
        self.search_project(self.TOTAL_PROJECTS)

        # after migrate (= rebuild_search)
        migrate(delete=False, remove=False,
                index=settings.ELASTIC_INDEX, app=self.app.app)
        self.search_contrib(self.TOTAL_USERS)
        self.search_project(self.TOTAL_PROJECTS)

    def test_rebuild_search_check_not_normalized(self):
        # If normalize() does not exist in migrate()
        with mock.patch('website.search_migration.migrate.normalize'):
            # after migrate (= rebuild_search)
            migrate(delete=False, remove=False,
                    index=settings.ELASTIC_INDEX, app=self.app.app)
        self.search_contrib(0)
        self.search_project(0)
