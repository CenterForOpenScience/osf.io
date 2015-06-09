# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from tests.base import ApiTestCase, fake
from rest_framework import generics, permissions as drf_permissions
from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory
from website.util.sanitize import strip_html


class TestUsers(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.save()
        self.user_two = UserFactory.build()
        self.user_two.save()

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_returns_200(self):
        res = self.app.get('/v2/users/')
        assert_equal(res.status_code, 200)

    def test_find_user_in_users(self):
        url = "/v2/users/"

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/v2/users/"

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/v2/users/?filter[fullname]=fred"

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/v2/users/?filter[fullname]=my"
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/v2/users/?filter[fullname]=NotMyMom"
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_not_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)


class TestUserDetail(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_gets_200(self):
        url = "/v2/users/{}/".format(self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_correct_pk_user(self):
        url = "/v2/users/{}/".format(self.user_one._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['social_accounts']['twitter'], 'howtopizza')

    def test_get_incorrect_pk_user_logged_in(self):
        url = "/v2/users/{}/".format(self.user_two._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)

    def test_get_incorrect_pk_user_not_logged_in(self):
        url = "/v2/users/{}/".format(self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['fullname'], self.user_two.fullname)


class TestUserNodes(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')
        self.user_one_url = '/v2/users/{}/'.format(self.user_one._id)
        self.user_two_url = '/v2/users/{}/'.format(self.user_two._id)
        self.public_project_user_one = ProjectFactory(title="Public Project User One", is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One", is_public=False, creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two", is_public=True, creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two", is_public=False, creator=self.user_two)
        self.deleted_project_user_one = FolderFactory(title="Deleted Project User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.folder = FolderFactory()
        self.deleted_folder = FolderFactory(title="Deleted Folder User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.dashboard = DashboardFactory()

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_authorized_in_gets_200(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_anonymous_gets_200(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_projects_logged_in(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_projects_not_logged_in(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_projects_logged_in_as_different_user(self):
        url = "/v2/users/{}/nodes/".format(self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_two._id, ids)
        assert_not_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)


class TestUserUpdate(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social_accounts = {
            'github': '',
            "scholar": "",
            "personal": 'http://mymom.com',
            "twitter": "billyhunt",
            "linkedIn": "",
            "impactStory": "",
            "orcid": "",
            "researcherId": ""
        }

        self.user_one.fullname = 'Martin Luther King Jr.'
        self.user_one.given_name = 'Martin'
        self.user_one.family_name = 'King'
        self.user_one.suffix = 'Jr.'
        self.user_one.employment_institutions = [
            {
                'startYear': '1995',
                'title': '',
                'startMonth': 1,
                'endMonth': None,
                'endYear': None,
                'ongoing': False,
                'department': '',
                'institution': 'Waffle House'
            }
        ]
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_one_url = "/v2/users/{}/".format(self.user_one._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')

        self.new_fullname = 'el-Hajj Malik el-Shabazz'
        self.new_given_name = 'Malcolm'
        self.new_family_name = 'X'
        self.new_suffix = 'Sr.'
        self.new_gravatar_url = 'https://secure.gravatar.com/avatar/220d886b6c6eb0503839261111679ebb?d=identicon&size=40'
        self.new_employment_institutions = [
            {
                'startYear': '1982',
                'title': '',
                'startMonth': 1,
                'endMonth': None,
                'endYear': None,
                'ongoing': True,
                'department': 'department of revolution',
                'institution': 'IHop'
            }
        ]

        self.new_educational_institutions = [
            {
                "startYear": "1999",
                "degree": "",
                "startMonth": None,
                "endMonth": None,
                "endYear": "2000",
                "ongoing": False,
                "department": "Mom",
                "institution": "Heeeyyyyyy"
            }
        ]

        self.new_social_accounts = {
            'github': 'mygit',
            'scholar': 'malcolmXScholar',
            'personal': 'http://mymom.com',
            'twitter': 'malcolmxtwitter',
            'linkedIn': 'malcolmxlinkedIn',
            'impactStory': 'malcolmximpackstory',
            'orcid': 'malcolmxorcid',
            'researcherId': 'malcolmxresearchid'
        }

    def test_patch_user_logged_out(self):
        res = self.app.patch_json(self.user_one_url, {
            'fullname': self.new_fullname,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_patch_user_logged_in(self):
        # Logged in user updates their user information via patch
        res = self.app.patch_json(self.user_one_url, {
            'fullname': self.new_fullname,
            'employment_institutions': self.new_employment_institutions,

        }, auth=self.auth_one)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['fullname'], self.new_fullname)

    def test_put_user_logged_in(self):
        # Logged in user updates their user information via patch
        res = self.app.put_json(self.user_one_url, {
            'id': self.user_one._id,
            'fullname': self.new_fullname,
            'social_accounts': self.new_social_accounts,
            'given_name': self.new_given_name,
            'family_name': self.new_family_name,
            'suffix': self.new_suffix,
            'employment_institutions': self.new_employment_institutions,
            'educational_institutions': self.new_educational_institutions,
            'gravatar_url': self.new_gravatar_url
        }, auth=self.auth_one)
        assert_equal(res.status_code, 200)
        # assert_equal(res.json['data']['fullname'], self.new_fullname)
        # assert_equal(res.json['data']['social_accounts'], self.new_social_accounts)
        # assert_equal(res.json['data']['given_name'], self.new_given_name)
        # assert_equal(res.json['data']['family_name'], self.new_family_name)
        # assert_equal(res.json['data']['suffix'], self.new_suffix)
        # assert_equal(res.json['data']['employment_institutions'], self.new_employment_institutions)
        # assert_equal(res.json['data']['educational_institutions'], self.new_educational_institutions)
        # assert_equal(res.json['data']['gravatar_url'], self.new_gravatar_url)

    def test_put_user_logged_out(self):
        res = self.app.put_json(self.user_one_url, {
            'fullname': self.new_fullname,
            'social_accounts': self.new_social_accounts,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_put_user_not_logged_in(self):
        # User tries to update someone else's user information via put
        res = self.app.put_json(self.user_one_url, {
            'fullname': self.new_fullname,
            'social_accounts': self.new_social_accounts,
            'given_name': self.new_given_name,
            'family_name': self.new_family_name,
            'suffix': self.new_suffix,
            'employment_institutions': self.new_employment_institutions,
        }, auth=self.auth_two, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_patch_wrong_user(self):
        # User tries to update someone else's user information via patch
        res = self.app.patch_json(self.user_one_url, {
            'fullname': self.new_fullname,
            'social_accounts': self.new_social_accounts,
        }, auth=self.auth_two, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_update_user_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        bad_fullname = 'Malcolm <strong>X</strong>'
        bad_family_name = 'X <script>alert("is")</script> a cool name'
        res = self.app.patch_json(self.user_one_url, {
            'fullname': bad_fullname,
            'family_name': bad_family_name,
        }, auth=self.auth_one)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['fullname'], strip_html(bad_fullname))
        assert_equal(res.json['data']['family_name'], strip_html(bad_family_name))
