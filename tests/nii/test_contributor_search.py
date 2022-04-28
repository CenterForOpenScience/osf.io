import pytest
import mock

from nose.tools import *  # noqa PEP8 asserts

from website import settings
import website.search.search as search
from website.search_migration.migrate import migrate
from website.search.util import build_query, build_query_string, validate_email

from tests.base import OsfTestCase
from tests.utils import run_celery_tasks
from osf_tests.factories import AuthUserFactory, InstitutionFactory, ProjectFactory
from osf_tests.test_elastic_search import retry_assertion
import time

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestContributorSearch(OsfTestCase):

    def setUp(self):
        super(TestContributorSearch, self).setUp()

        with run_celery_tasks():
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
        assert_equal(sorted(set([u['fullname'] for u in contribs['users']])),
                     sorted(set(self.inst1_users)))

        # two institutions
        contribs = search_contribs(self.user2)
        assert_equal(sorted(set([u['fullname'] for u in contribs['users']])),
                     sorted(set(self.inst1_users) | set(self.inst2_users)))

        # independent (no institution) -> from all institutions
        contribs = search_contribs(self.user3)
        assert_equal(len(contribs['users']), 7)

    def test_search_contributors_from_my_institutions_after_rebuild_search(self):
        migrate(delete=False, remove=False,
                index=None, app=self.app.app)
        # after migrate (= rebuild_search)
        self.test_search_contributors_from_my_institutions()

    def test_search_contributors_by_guid(self):
        contribs = search.search_contributor(
            self.user2._id,
            current_user=self.user1
        )
        assert_equal(set([u['fullname'] for u in contribs['users']]),
                     set([self.user2.fullname]))

    def test_search_contributors_by_email(self):
        email2 = self.user2.emails.get()
        email2.address = 'test@example.com'
        email2.save()
        migrate(delete=False, remove=False,
                index=None, app=self.app.app)
        time.sleep(10)
        contribs = search.search_contributor(
            email2.address,
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

        assert_equal(es_escape(string.ascii_letters), string.ascii_letters)
        assert_equal(es_escape(string.octdigits), string.octdigits)
        assert_equal(es_escape(string.whitespace), string.whitespace)

        hiragana = ''.join([chr(i) for i in range(12353, 12436)])
        assert_equal(es_escape(hiragana), hiragana)

        katakana = ''.join([chr(i) for i in range(12449, 12533)])
        assert_equal(es_escape(katakana), katakana)

        zenkaku_hankaku = ''.join([chr(i) for i in range(65281, 65440)])
        assert_equal(es_escape(zenkaku_hankaku), zenkaku_hankaku)


# see ./osf_tests/test_elastic_search.py
@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchMigrationNormalizedField(OsfTestCase):

    # This feature is unsupported when ENABLE_MULTILINGUAL_SEARCH is True.

    @classmethod
    def tearDownClass(cls):
        super(TestSearchMigrationNormalizedField, cls).tearDownClass()
        search.create_index()

    def setUp(self):
        super(TestSearchMigrationNormalizedField, self).setUp()
        self.es = search.search_engine.CLIENT
        search.delete_all()
        search.create_index()

        with run_celery_tasks():
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
                          index=None, raw=False)
        assert_equal(len(r['results']), expect_num)

    def test_rebuild_search_check_normalized(self):
        self.search_contrib(self.TOTAL_USERS)
        self.search_project(self.TOTAL_PROJECTS)

        # after update_search()
        for u in self.users:
            u.update_search()
        self.search_contrib(self.TOTAL_USERS)
        self.search_project(self.TOTAL_PROJECTS)

        migrate(delete=False, remove=True,
                index=None, app=self.app.app)
        # after migrate (= rebuild_search)
        self.search_contrib(self.TOTAL_USERS)
        self.search_project(self.TOTAL_PROJECTS)

    def test_rebuild_search_check_not_normalized(self):
        with mock.patch('website.search_migration.migrate.fill_and_normalize'):
            migrate(delete=False, remove=True,
                    index=None, app=self.app.app)
            # after migrate (= rebuild_search)

        self.search_contrib(0)
        self.search_project(0)

class TestSearchUtils(OsfTestCase):

    def test_build_query_with_match_key_and_match_value_valid(self):
        query_body = build_query_string('*')
        match_key = 'id'
        match_value = 'f8pzw'
        start = 0
        size = 10
        query_body = {
            'bool': {
                'should': [
                    query_body,
                    {
                        'match': {
                            match_key: {
                                'query': match_value,
                                'boost': 10.0
                            }
                        }
                    }
                ]
            }
        }

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        assert_is_instance(res, dict)
        assert_equal(res, expectedResult)

    def test_build_query_with_match_key_is_email_and_match_value_valid(self):
        match_key = 'emails'
        match_value = 'test@example.com'
        start = 0
        size = 10
        build_query_emails = 'emails:' + match_value
        query_body = {
            'bool': {
                'should': [
                    {
                        'query_string': {
                            'default_operator': 'AND',
                            'query': build_query_emails
                        }
                    }
                ]
            }
        }

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        assert_is_instance(res, dict)
        assert_equal(res, expectedResult)

    def test_build_query_with_match_key_and_match_value_invalid(self):
        query_body = build_query_string('*')
        match_key = 1
        match_value = None
        start = 0
        size = 10

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        assert_is_instance(res, dict)
        assert_equal(res, expectedResult)

    def test_build_query_with_match_key_invalid_and_match_value(self):
        query_body = build_query_string('*')
        match_key = 1
        match_value = 'f8pzw'
        start = 0
        size = 10

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        assert_is_instance(res, dict)
        assert_equal(res, expectedResult)

    def test_validate_email_is_not_none(self):
        self.email = 'roger@queen.com'
        result = validate_email(self.email)
        assert_equal(result, True)

        result2 = validate_email('')
        assert_equal(result2, False)

        result3 = validate_email('"joe bloggs"@b.c')
        assert_equal(result3, False)

        result4 = validate_email('a@b.c')
        assert_equal(result4, False)

        result5 = validate_email('a@b.c@')
        assert_equal(result5, False)

    def test_validate_email_is_none(self):
        self.email = None
        result = validate_email(self.email)
        assert_equal(result, False)
