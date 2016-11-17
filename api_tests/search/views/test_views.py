from modularodm import Q
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from api_tests import utils

from framework.auth.core import Auth

from tests.base import ApiTestCase
from tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
)
from tests.utils import mock_archive

from website.models import MetaSchema
from website.project.model import ensure_schemas
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from website.search import search


class ApiSearchTestCase(ApiTestCase):

    def setUp(self):
        super(ApiSearchTestCase, self).setUp()

        self.user = AuthUserFactory()
        self.user_one = AuthUserFactory(fullname='Kanye Omari West')
        self.user_one.schools = [{
            'degree': 'English',
            'institution': 'Chicago State University'
        }]
        self.user_one.jobs = [{
            'title': 'Producer',
            'institution': 'GOOD Music, Inc.'
        }]
        self.user_one.save()

        self.user_two = AuthUserFactory(fullname='Chance The Rapper')

        self.project = ProjectFactory(title='The Life of Pablo', creator=self.user_one, is_public=True)
        self.project.set_description('Name one genius who ain\'t crazy', auth=Auth(self.user_one), save=True)
        self.project.add_tag('Yeezus', auth=Auth(self.user_one), save=True)

        self.project_two = ProjectFactory(title='Graduation', creator=self.user_one, is_public=True)
        self.private_project = ProjectFactory(title='Coloring Book', creator=self.user_two)

        self.component = NodeFactory(parent=self.project, title='Ultralight Beam', creator=self.user_two, is_public=True)
        self.component.set_description('This is my part, nobody else speak', auth=Auth(self.user_two), save=True)
        self.component.add_tag('trumpets', auth=Auth(self.user_two), save=True)

        self.component_two = NodeFactory(parent=self.project, title='Highlights', creator=self.user_one, is_public=True)
        self.private_component = NodeFactory(parent=self.project, title='Wavves', creator=self.user_one)

        self.file = utils.create_test_file(self.component, self.user_one, filename='UltralightBeam.mp3')
        self.file_two = utils.create_test_file(self.component_two, self.user_one, filename='Highlights.mp3')
        self.private_file = utils.create_test_file(self.private_component, self.user_one, filename='Wavves.mp3')

    def tearDown(self):
        super(ApiSearchTestCase, self).tearDown()
        search.delete_all()


class TestSearch(ApiSearchTestCase):

    def setUp(self):
        super(TestSearch, self).setUp()
        self.url = '/{}search/'.format(API_BASE)

    def test_search_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)

        search_fields = res.json['search_fields']
        users_found = search_fields['users']['related']['meta']['total']
        files_found = search_fields['files']['related']['meta']['total']
        projects_found = search_fields['projects']['related']['meta']['total']
        components_found = search_fields['components']['related']['meta']['total']
        registrations_found = search_fields['registrations']['related']['meta']['total']

        assert_equal(users_found, 3)
        assert_equal(files_found, 2)
        assert_equal(projects_found, 2)
        assert_equal(components_found, 2)
        assert_equal(registrations_found, 0)

    def test_search_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)

        search_fields = res.json['search_fields']
        users_found = search_fields['users']['related']['meta']['total']
        files_found = search_fields['files']['related']['meta']['total']
        projects_found = search_fields['projects']['related']['meta']['total']
        components_found = search_fields['components']['related']['meta']['total']
        registrations_found = search_fields['registrations']['related']['meta']['total']

        assert_equal(users_found, 3)
        assert_equal(files_found, 2)
        assert_equal(projects_found, 2)
        assert_equal(components_found, 2)
        assert_equal(registrations_found, 0)

    def test_search_fields_links(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)

        search_fields = res.json['search_fields']
        users_link = search_fields['users']['related']['href']
        files_link = search_fields['files']['related']['href']
        projects_link = search_fields['projects']['related']['href']
        components_link = search_fields['components']['related']['href']
        registrations_link = search_fields['registrations']['related']['href']

        assert_in('/{}search/users/?q=*'.format(API_BASE), users_link)
        assert_in('/{}search/files/?q=*'.format(API_BASE), files_link)
        assert_in('/{}search/projects/?q=*'.format(API_BASE), projects_link)
        assert_in('/{}search/components/?q=*'.format(API_BASE), components_link)
        assert_in('/{}search/registrations/?q=*'.format(API_BASE), registrations_link)

    def test_search_fields_links_with_query(self):
        url = '{}?q=science'.format(self.url)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

        search_fields = res.json['search_fields']
        users_link = search_fields['users']['related']['href']
        files_link = search_fields['files']['related']['href']
        projects_link = search_fields['projects']['related']['href']
        components_link = search_fields['components']['related']['href']
        registrations_link = search_fields['registrations']['related']['href']

        assert_in('/{}search/users/?q=science'.format(API_BASE), users_link)
        assert_in('/{}search/files/?q=science'.format(API_BASE), files_link)
        assert_in('/{}search/projects/?q=science'.format(API_BASE), projects_link)
        assert_in('/{}search/components/?q=science'.format(API_BASE), components_link)
        assert_in('/{}search/registrations/?q=science'.format(API_BASE), registrations_link)


class TestSearchComponents(ApiSearchTestCase):

    def setUp(self):
        super(TestSearchComponents, self).setUp()
        self.url = '/{}search/components/'.format(API_BASE)

    def test_search_public_component_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.component.title, res)
        assert_in(self.component_two.title, res)

    def test_search_public_component_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.component.title, res)
        assert_in(self.component_two.title, res)

    def test_search_public_component_contributor(self):
        res = self.app.get(self.url, auth=self.user_two)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.component.title, res)
        assert_in(self.component_two.title, res)

    def test_search_private_component_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_component.title, res)

    def test_search_private_component_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_component.title, res)

    def test_search_private_component_contributor(self):
        res = self.app.get(self.url, auth=self.user_two)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_component.title, res)

    def test_search_component_by_title(self):
        url = '{}?q={}'.format(self.url, 'beam')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.component.title, res.json['data'][0]['attributes']['title'])

    def test_search_component_by_description(self):
        url = '{}?q={}'.format(self.url, 'speak')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.component.title, res.json['data'][0]['attributes']['title'])

    def test_search_component_by_tags(self):
        url = '{}?q={}'.format(self.url, 'trumpets')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.component.title, res.json['data'][0]['attributes']['title'])

    def test_search_component_by_contributor(self):
        url = '{}?q={}'.format(self.url, 'Chance')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.component.title, res.json['data'][0]['attributes']['title'])

    def test_search_component_no_results(self):
        url = '{}?q={}'.format(self.url, 'Ocean')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 0)

    def test_search_component_bad_query(self):
        url = '{}?q={}'.format(self.url, 'www.spam.com/help/twitter/')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)


class TestSearchFiles(ApiSearchTestCase):

    def setUp(self):
        super(TestSearchFiles, self).setUp()
        self.url = '/{}search/files/'.format(API_BASE)

    def test_search_public_file_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.file.name, res)
        assert_in(self.file_two.name, res)

    def test_search_public_file_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.file.name, res)
        assert_in(self.file_two.name, res)

    def test_search_public_file_contributor(self):
        res = self.app.get(self.url, auth=self.user_one)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.file.name, res)
        assert_in(self.file_two.name, res)

    def test_search_private_file_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_file.name, res)

    def test_search_private_file_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_file.name, res)

    def test_search_private_file_contributor(self):
        res = self.app.get(self.url, auth=self.user_one)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_file.name, res)

    def test_search_file_by_name(self):
        url = '{}?q={}'.format(self.url, 'highlights')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.file_two.name, res.json['data'][0]['attributes']['name'])


class TestSearchProjects(ApiSearchTestCase):

    def setUp(self):
        super(TestSearchProjects, self).setUp()
        self.url = '/{}search/projects/'.format(API_BASE)

    def test_search_public_project_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.project.title, res)
        assert_in(self.project_two.title, res)

    def test_search_public_project_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.project.title, res)
        assert_in(self.project_two.title, res)

    def test_search_public_project_contributor(self):
        res = self.app.get(self.url, auth=self.user_one)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.project.title, res)
        assert_in(self.project_two.title, res)

    def test_search_private_project_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_project.title, res)

    def test_search_private_project_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_project.title, res)

    def test_search_private_project_contributor(self):
        res = self.app.get(self.url, auth=self.user_two)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_project.title, res)

    def test_search_project_by_title(self):
        url = '{}?q={}'.format(self.url, 'pablo')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.project.title, res.json['data'][0]['attributes']['title'])

    def test_search_project_by_description(self):
        url = '{}?q={}'.format(self.url, 'genius')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.project.title, res.json['data'][0]['attributes']['title'])

    def test_search_project_by_tags(self):
        url = '{}?q={}'.format(self.url, 'yeezus')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.project.title, res.json['data'][0]['attributes']['title'])

    def test_search_project_by_contributor(self):
        url = '{}?q={}'.format(self.url, 'kanye')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.project.title, res)
        assert_in(self.project_two.title, res)

    def test_search_project_no_results(self):
        url = '{}?q={}'.format(self.url, 'chicago')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 0)

    def test_search_project_bad_query(self):
        url = '{}?q={}'.format(self.url, 'www.spam.com/help/facebook/')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)


class TestSearchRegistrations(ApiSearchTestCase):

    def setUp(self):
        super(TestSearchRegistrations, self).setUp()
        self.url = '/{}search/registrations/'.format(API_BASE)

        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'Replication Recipe (Brandt et al., 2013): Post-Completion') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )

        with mock_archive(self.project, autocomplete=True, autoapprove=True, schema=self.schema) as registration:
            self.registration = registration

        with mock_archive(self.project_two, autocomplete=True, autoapprove=True,
                          schema=self.schema) as registration_two:
            self.registration_two = registration_two

        with mock_archive(self.private_project, autocomplete=True, autoapprove=True,
                          schema=self.schema) as private_registration:
            self.private_registration = private_registration

        self.private_registration.is_public = False
        self.private_registration.save()

    def test_search_public_registration_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.registration.title, res)
        assert_in(self.registration_two.title, res)

    def test_search_public_registration_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.registration.title, res)
        assert_in(self.registration_two.title, res)

    def test_search_public_registration_contributor(self):
        res = self.app.get(self.url, auth=self.user_one)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.registration.title, res)
        assert_in(self.registration_two.title, res)

    def test_search_private_registration_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_registration.title, res)

    def test_search_private_registration_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_registration.title, res)

    def test_search_private_registration_contributor(self):
        res = self.app.get(self.url, auth=self.user_two)
        assert_equal(res.status_code, 200)
        assert_not_in(self.private_registration.title, res)

    def test_search_registration_by_title(self):
        url = '{}?q={}'.format(self.url, 'graduation')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.registration_two.title, res.json['data'][0]['attributes']['title'])

    def test_search_registration_by_description(self):
        url = '{}?q={}'.format(self.url, 'crazy')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.registration.title, res.json['data'][0]['attributes']['title'])

    def test_search_registration_by_tags(self):
        url = '{}?q={}'.format(self.url, 'yeezus')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.registration.title, res.json['data'][0]['attributes']['title'])

    def test_search_registration_by_contributor(self):
        url = '{}?q={}'.format(self.url, 'west')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.registration.title, res)
        assert_in(self.registration_two.title, res)

    def test_search_registration_no_results(self):
        url = '{}?q={}'.format(self.url, '79th')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 0)

    def test_search_registration_bad_query(self):
        url = '{}?q={}'.format(self.url, 'www.spam.com/help/snapchat/')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)


class TestSearchUsers(ApiSearchTestCase):

    def setUp(self):
        super(TestSearchUsers, self).setUp()
        self.url = '/{}search/users/'.format(API_BASE)

    def test_search_users_no_auth(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.user.fullname, res)
        assert_in(self.user.fullname, res)

    def test_search_users_auth(self):
        res = self.app.get(self.url, auth=self.user)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 2)
        assert_in(self.user.fullname, res)
        assert_in(self.user.fullname, res)

    def test_search_users_by_given_name(self):
        url = '{}?q={}'.format(self.url, 'Kanye')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.user_one.given_name, res.json['data'][0]['attributes']['given_name'])

    def test_search_users_by_middle_name(self):
        url = '{}?q={}'.format(self.url, 'Omari')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.user_one.middle_names[0], res.json['data'][0]['attributes']['middle_names'][0])

    def test_search_users_by_family_name(self):
        url = '{}?q={}'.format(self.url, 'West')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.user_one.family_name, res.json['data'][0]['attributes']['family_name'])

    def test_search_users_by_job(self):
        url = '{}?q={}'.format(self.url, 'producer')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.user_one.fullname, res.json['data'][0]['attributes']['full_name'])

    def test_search_users_by_school(self):
        url = '{}?q={}'.format(self.url, 'Chicago')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert_equal(num_results, total, 1)
        assert_equal(self.user_one.fullname, res.json['data'][0]['attributes']['full_name'])
