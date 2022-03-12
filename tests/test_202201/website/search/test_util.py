from nose import tools as nt
from tests.base import OsfTestCase
from website.search import util
from tests.utils import run_celery_tasks
from osf_tests.factories import AuthUserFactory, InstitutionFactory, ProjectFactory
import website.search.search as search
from website.search_migration.migrate import migrate
import time
import pytest


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
        nt.assert_equal(set([u['fullname'] for u in contribs['users']]),
                     set([self.user2.fullname]))


class TestSearchUtils(OsfTestCase):

    def test_build_query_with_match_key_and_match_value_valid(self):
        query_body = util.build_query_string('*')
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
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

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
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

    def test_build_query_with_match_key_invalid_and_match_value(self):
        query_body = util.build_query_string('*')
        match_key = 1
        match_value = 'f8pzw'
        start = 0
        size = 10

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

    def test_build_query_with_match_key_and_match_value_invalid(self):
        query_body = util.build_query_string('*')
        match_key = 1
        match_value = None
        start = 0
        size = 10

        expectedResult = {
            'query': query_body,
            'from': start,
            'size': size,
        }
        res = util.build_query(start=start, size=size,
                               match_value=match_value, match_key=match_key)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res, expectedResult)

    def test_validate_email_is_not_none(self):
        self.email = 'roger@queen.com'
        result = util.validate_email(self.email)
        nt.assert_equal(result, True)

        result2 = util.validate_email('')
        nt.assert_equal(result2, False)

        result3 = util.validate_email('"joe bloggs"@b.c')
        nt.assert_equal(result3, False)

        result4 = util.validate_email('a@b.c')
        nt.assert_equal(result4, False)

        result5 = util.validate_email('a@b.c@')
        nt.assert_equal(result5, False)

    def test_validate_email_is_none(self):
        self.email = None
        result = util.validate_email(self.email)
        nt.assert_equal(result, False)
