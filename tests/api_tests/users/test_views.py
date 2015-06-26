# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from website.models import Node
from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE

from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory
from website.util.sanitize import strip_html


class TestUsers(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.fullname = 'Martin Luther King Jr.'
        self.user_one.given_name = 'Martin'
        self.user_one.family_name = 'King'
        self.user_one.suffix = 'Jr.'
        self.user_one.social['github'] = 'userOneGithub'
        self.user_one.social['scholar'] = 'userOneScholar'
        self.user_one.social['personal_website'] = 'http://www.useronepersonalwebsite.com'
        self.user_one.social['twitter'] = 'userOneTwitter'
        self.user_one.social['linkedIn'] = 'userOneLinkedIn'
        self.user_one.social['impactStory'] = 'userOneImpactStory'
        self.user_one.social['orcid'] = 'userOneOrcid'
        self.user_one.social['researcherId'] = 'userOneResearcherId'

        self.user_one.employment_institutions = [
            {
                'startYear': '1954',
                'title': '',
                'startMonth': 1,
                'endMonth': None,
                'endYear': 1968,
                'ongoing': False,
                'department': '',
                'institution': 'Dexter Avenue Baptist Church'
            },
        ]
        self.user_one.save()

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.fullname = 'Martin Lawrence'
        self.user_two.given_name = 'Martin'
        self.user_two.family_name = 'Lawrence'
        self.user_two.suffix = 'Sr.'
        self.user_two.social['github'] = 'userTwoGithub'
        self.user_two.social['scholar'] = 'userTwoScholar'
        self.user_two.social['personal_website'] = 'http://www.useronepersonalwebsite.com'
        self.user_two.social['twitter'] = 'userTwoTwitter'
        self.user_two.social['linkedIn'] = 'userTwoLinkedIn'
        self.user_two.social['impactStory'] = 'userTwoImpactStory'
        self.user_two.social['orcid'] = 'userTwoOrcid'
        self.user_two.social['researcherId'] = 'userTwoResearcherId'

        self.user_two.employment_institutions = [
            {
                'startYear': '1900',
                'title': 'Martin',
                'startMonth': 1,
                'endMonth': None,
                'endYear': None,
                'ongoing': True,
                'department': '',
                'institution': 'Waffle House'
            },
            {
                "startYear": '',
                "title": 'President of Tony Danza Management',
                "startMonth": None,
                "endMonth": None,
                "endYear": '2000',
                "ongoing": False,
                "department": 'Mom',
                "institution": 'Heeyyyy'
            },
        ]

        self.user_two.save()

        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.auth_two = (self.user_two.username, 'justapoorboy')

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_returns_200(self):
        res = self.app.get('/{}users/'.format(API_BASE))
        assert_equal(res.status_code, 200)

    def test_find_user_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/{}users/?filter[fullname]=Martin".format(API_BASE)

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/{}users/?filter[fullname]=Mom".format(API_BASE)
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_filter_using_user_id(self):
        url = "/{}users/?filter[id]={}".format(API_BASE, self.user_one._id)
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_filter_using_complex_field(self):
        url = "/{}users/?filter[employment_institutions.title]=Martin".format(API_BASE)
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/{}users/?filter[given_name]=notMartin".format(API_BASE)
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
        self.user_one.fullname = 'Martin Luther King Jr.'
        self.user_one.given_name = 'Martin'
        self.user_one.family_name = 'King'
        self.user_one.suffix = 'Jr.'
        self.user_one.social['github'] = 'userOneGithub'
        self.user_one.social['scholar'] = 'userOneScholar'
        self.user_one.social['personal_website'] = 'http://www.useronepersonalwebsite.com'
        self.user_one.social['twitter'] = 'userOneTwitter'
        self.user_one.social['linkedIn'] = 'userOneLinkedIn'
        self.user_one.social['impactStory'] = 'userOneImpactStory'
        self.user_one.social['orcid'] = 'userOneOrcid'
        self.user_one.social['researcherId'] = 'userOneResearcherId'

        self.user_one.employment_institutions = [
            {
                'startYear': '1954',
                'title': '',
                'startMonth': 1,
                'endMonth': None,
                'endYear': 1968,
                'ongoing': False,
                'department': '',
                'institution': 'Dexter Avenue Baptist Church'
            },
        ]
        self.user_one.save()

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.fullname = 'Martin Lawrence'
        self.user_two.given_name = 'Martin'
        self.user_two.family_name = 'Lawrence'
        self.user_two.suffix = 'Sr.'
        self.user_two.social['github'] = 'userTwoGithub'
        self.user_two.social['scholar'] = 'userTwoScholar'
        self.user_two.social['personal_website'] = 'http://www.useronepersonalwebsite.com'
        self.user_two.social['twitter'] = 'userTwoTwitter'
        self.user_two.social['linkedIn'] = 'userTwoLinkedIn'
        self.user_two.social['impactStory'] = 'userTwoImpactStory'
        self.user_two.social['orcid'] = 'userTwoOrcid'
        self.user_two.social['researcherId'] = 'userTwoResearcherId'

        self.user_two.employment_institutions = [
            {
                'startYear': '1900',
                'title': '',
                'startMonth': 1,
                'endMonth': None,
                'endYear': None,
                'ongoing': True,
                'department': '',
                'institution': 'Waffle House'
            },
            {
                "startYear": '',
                "title": 'President of Tony Danza Management',
                "startMonth": None,
                "endMonth": None,
                "endYear": '2000',
                "ongoing": False,
                "department": 'Mom',
                "institution": 'Heeyyyy'
            },
        ]

        self.user_two.save()

        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.auth_two = (self.user_two.username, 'justapoorboy')

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_gets_200(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_correct_pk_user(self):
        url = "/{}users/{}/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['twitter'], self.user_one.social['twitter'])
        assert_equal(user_json['family_name'], self.user_one.family_name)

    def test_get_incorrect_pk_user_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)

    def test_get_incorrect_pk_user_not_logged_in(self):
        url = "/{}users/{}/".format(API_BASE, self.user_two._id)
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
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_anonymous_gets_200(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_projects_logged_in(self):
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
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
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_one._id)
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
        url = "/{}users/{}/nodes/".format(API_BASE, self.user_two._id)
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
        self.user_one.fullname = 'Martin Luther King Jr.'
        self.user_one.given_name = 'Martin'
        self.user_one.family_name = 'King'
        self.user_one.suffix = 'Jr.'
        self.user_one.github = 'userOneGithub'
        self.user_one.scholar = 'userOneScholar'
        self.user_one.personal_website = 'http://www.useronepersonalwebsite.com'
        self.user_one.twitter = 'userOneTwitter'
        self.user_one.linkedIn = 'userOneLinkedIn'
        self.user_one.impactStory = 'userOneImpactStory'
        self.user_one.orcid = 'userOneOrcid'
        self.user_one.researcherId = 'userOneResearcherId'

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
        self.new_employment_institutions = [
            {
                'startYear': '1982',
                'title': '',
                'startMonth': 1,
                'endMonth': 4,
                'endYear': 1999,
                'ongoing': True,
                'department': 'department of revolution',
                'institution': 'IHop'
            }
        ]

        self.new_educational_institutions = [
            {
                "startYear": '',
                "degree": '',
                "startMonth": None,
                "endMonth": None,
                "endYear": '2000',
                "ongoing": False,
                "department": 'Mom',
                "institution": 'Heeyyyy'
            }
        ]

        self.newGithub = 'newGithub'
        self.newScholar = 'newScholar'
        self.newPersonal_website = 'http://www.newpersonalwebsite.com'
        self.newTwitter = 'newTwitter'
        self.newLinkedIn = 'newLinkedIn'
        self.newImpactStory = 'newImpactStory'
        self.newOrcid = 'newOrcid'
        self.newResearcherId = 'newResearcherId'

    def test_patch_user_logged_out(self):
        res = self.app.patch_json(self.user_one_url, {
            'fullname': self.new_fullname,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_patch_user_read_only_field(self):
        # Logged in user updates their user information via patch
        res = self.app.patch_json(self.user_one_url, {
            'employment_institutions': self.new_employment_institutions,
            'educational_institutions': self.new_educational_institutions,
            'fullname': self.new_fullname,

        }, auth=self.auth_one)
        print res
        assert_equal(res.status_code, 200)
        assert_not_equal(res.json['data']['employment_institutions'], self.new_employment_institutions)
        assert_not_equal(res.json['data']['educational_institutions'], self.new_educational_institutions)
        # assert_equal(res.json['data']['employment_institutions'], self.user_one.employment_institutions)
        assert_equal(res.json['data']['fullname'], self.new_fullname)

    def test_put_user_logged_in(self):
        # Logged in user updates their user information via patch
        res = self.app.put_json(self.user_one_url, {
            'id': self.user_one._id,
            'fullname': self.new_fullname,
            'given_name': self.new_given_name,
            'family_name': self.new_family_name,
            'suffix': self.new_suffix,
            'github': self.newGithub,
            'personal_website': self.newPersonal_website,
            'twitter': self.newTwitter,
            'linkedIn': self.newLinkedIn,
            'impactStory': self.newImpactStory,
            'orcid': self.newOrcid,
            'researcherId': self.newResearcherId,
        }, auth=self.auth_one)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['fullname'], self.new_fullname)
        assert_equal(res.json['data']['given_name'], self.new_given_name)
        assert_equal(res.json['data']['family_name'], self.new_family_name)
        assert_equal(res.json['data']['suffix'], self.new_suffix)
        assert_equal(res.json['data']['github'], self.newGithub)
        assert_equal(res.json['data']['personal_website'], self.newPersonal_website)
        assert_equal(res.json['data']['twitter'], self.newTwitter)
        assert_equal(res.json['data']['linkedIn'], self.newLinkedIn)
        assert_equal(res.json['data']['impactStory'], self.newImpactStory)
        assert_equal(res.json['data']['orcid'], self.newOrcid)
        assert_equal(res.json['data']['researcherId'], self.newResearcherId)

    def test_put_user_logged_out(self):
        res = self.app.put_json(self.user_one_url, {
            'id': self.user_one._id,
            'fullname': self.new_fullname,
            'given_name': self.new_given_name,
            'family_name': self.new_family_name,
            'suffix': self.new_suffix,
            'github': self.newGithub,
            'personal_website': self.newPersonal_website,
            'twitter': self.newTwitter,
            'linkedIn': self.newLinkedIn,
            'impactStory': self.newImpactStory,
            'orcid': self.newOrcid,
            'researcherId': self.newResearcherId,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_put_user_not_logged_in(self):
        # User tries to update someone else's user information via put
        res = self.app.put_json(self.user_one_url, {
            'id': self.user_one._id,
            'fullname': self.new_fullname,
            'given_name': self.new_given_name,
            'family_name': self.new_family_name,
            'suffix': self.new_suffix,
            'github': self.newGithub,
            'personal_website': self.newPersonal_website,
            'twitter': self.newTwitter,
            'linkedIn': self.newLinkedIn,
            'impactStory': self.newImpactStory,
            'orcid': self.newOrcid,
            'researcherId': self.newResearcherId,
        }, auth=self.auth_two, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_patch_wrong_user(self):
        # User tries to update someone else's user information via patch
        res = self.app.patch_json(self.user_one_url, {
            'fullname': self.new_fullname,
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
