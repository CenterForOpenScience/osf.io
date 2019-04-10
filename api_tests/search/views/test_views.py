import pytest
import uuid

from api.base.settings.defaults import API_BASE
from api_tests import utils
from framework.auth.core import Auth
from osf.models import RegistrationSchema
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    InstitutionFactory,
    CollectionFactory,
    CollectionProviderFactory,
    RegistrationProviderFactory,
)
from osf_tests.utils import mock_archive
from website import settings
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from website.search import elastic_search
from website.search import search


@pytest.mark.django_db
@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class ApiSearchTestCase:

    @pytest.fixture(autouse=True)
    def index(self):
        settings.ELASTIC_INDEX = uuid.uuid4().hex
        elastic_search.INDEX = settings.ELASTIC_INDEX

        search.create_index(elastic_search.INDEX)
        yield
        search.delete_index(elastic_search.INDEX)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory(name='Social Experiment')

    @pytest.fixture()
    def collection_public(self, user):
        return CollectionFactory(creator=user, provider=CollectionProviderFactory(), is_public=True,
                                 status_choices=['', 'asdf', 'lkjh'], collected_type_choices=['', 'asdf', 'lkjh'],
                                 issue_choices=['', '0', '1', '2'], volume_choices=['', '0', '1', '2'],
                                 program_area_choices=['', 'asdf', 'lkjh'])

    @pytest.fixture()
    def registration_collection(self, user):
        return CollectionFactory(creator=user, provider=RegistrationProviderFactory(), is_public=True,
                                 status_choices=['', 'asdf', 'lkjh'], collected_type_choices=['', 'asdf', 'lkjh'])

    @pytest.fixture()
    def user_one(self):
        user_one = AuthUserFactory(fullname='Kanye Omari West')
        user_one.schools = [{
            'degree': 'English',
            'institution': 'Chicago State University'
        }]
        user_one.jobs = [{
            'title': 'Producer',
            'institution': 'GOOD Music, Inc.'
        }]
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self, institution):
        user_two = AuthUserFactory(fullname='Chance The Rapper')
        user_two.affiliated_institutions.add(institution)
        user_two.save()
        return user_two

    @pytest.fixture()
    def project(self, user_one):
        return ProjectFactory(
            title='Graduation',
            creator=user_one,
            is_public=True)

    @pytest.fixture()
    def project_public(self, user_one):
        project_public = ProjectFactory(
            title='The Life of Pablo',
            creator=user_one,
            is_public=True)
        project_public.set_description(
            'Name one genius who ain\'t crazy',
            auth=Auth(user_one),
            save=True)
        project_public.add_tag('Yeezus', auth=Auth(user_one), save=True)
        return project_public

    @pytest.fixture()
    def project_private(self, user_two):
        return ProjectFactory(title='Coloring Book', creator=user_two)

    @pytest.fixture()
    def component(self, user_one, project_public):
        return NodeFactory(
            parent=project_public,
            title='Highlights',
            description='',
            creator=user_one,
            is_public=True)

    @pytest.fixture()
    def component_public(self, user_two, project_public):
        component_public = NodeFactory(
            parent=project_public,
            title='Ultralight Beam',
            creator=user_two,
            is_public=True)
        component_public.set_description(
            'This is my part, nobody else speak',
            auth=Auth(user_two),
            save=True)
        component_public.add_tag('trumpets', auth=Auth(user_two), save=True)
        return component_public

    @pytest.fixture()
    def component_private(self, user_one, project_public):
        return NodeFactory(
            parent=project_public,
            description='',
            title='Wavves',
            creator=user_one)

    @pytest.fixture()
    def file_component(self, component, user_one):
        return utils.create_test_file(
            component, user_one, filename='Highlights.mp3')

    @pytest.fixture()
    def file_public(self, component_public, user_one):
        return utils.create_test_file(
            component_public,
            user_one,
            filename='UltralightBeam.mp3')

    @pytest.fixture()
    def file_private(self, component_private, user_one):
        return utils.create_test_file(
            component_private, user_one, filename='Wavves.mp3')


class TestSearch(ApiSearchTestCase):

    @pytest.fixture()
    def url_search(self):
        return '/{}search/'.format(API_BASE)

    def test_search_results(
            self, app, url_search, user, user_one, user_two,
            institution, component, component_private,
            component_public, file_component, file_private,
            file_public, project, project_public, project_private):

        # test_search_no_auth
        res = app.get(url_search)
        assert res.status_code == 200

        search_fields = res.json['search_fields']
        users_found = search_fields['users']['related']['meta']['total']
        files_found = search_fields['files']['related']['meta']['total']
        projects_found = search_fields['projects']['related']['meta']['total']
        components_found = search_fields['components']['related']['meta']['total']
        registrations_found = search_fields['registrations']['related']['meta']['total']

        assert users_found == 3
        assert files_found == 2
        assert projects_found == 2
        assert components_found == 2
        assert registrations_found == 0

        # test_search_auth
        res = app.get(url_search, auth=user.auth)
        assert res.status_code == 200

        search_fields = res.json['search_fields']
        users_found = search_fields['users']['related']['meta']['total']
        files_found = search_fields['files']['related']['meta']['total']
        projects_found = search_fields['projects']['related']['meta']['total']
        components_found = search_fields['components']['related']['meta']['total']
        registrations_found = search_fields['registrations']['related']['meta']['total']

        assert users_found == 3
        assert files_found == 2
        assert projects_found == 2
        assert components_found == 2
        assert registrations_found == 0

        # test_search_fields_links
        res = app.get(url_search)
        assert res.status_code == 200

        search_fields = res.json['search_fields']
        users_link = search_fields['users']['related']['href']
        files_link = search_fields['files']['related']['href']
        projects_link = search_fields['projects']['related']['href']
        components_link = search_fields['components']['related']['href']
        registrations_link = search_fields['registrations']['related']['href']

        assert '/{}search/users/?q=%2A'.format(API_BASE) in users_link
        assert '/{}search/files/?q=%2A'.format(API_BASE) in files_link
        assert '/{}search/projects/?q=%2A'.format(API_BASE) in projects_link
        assert '/{}search/components/?q=%2A'.format(
            API_BASE) in components_link
        assert '/{}search/registrations/?q=%2A'.format(
            API_BASE) in registrations_link

        # test_search_fields_links_with_query
        url = '{}?q=science'.format(url_search)
        res = app.get(url)
        assert res.status_code == 200

        search_fields = res.json['search_fields']
        users_link = search_fields['users']['related']['href']
        files_link = search_fields['files']['related']['href']
        projects_link = search_fields['projects']['related']['href']
        components_link = search_fields['components']['related']['href']
        registrations_link = search_fields['registrations']['related']['href']

        assert '/{}search/users/?q=science'.format(API_BASE) in users_link
        assert '/{}search/files/?q=science'.format(API_BASE) in files_link
        assert '/{}search/projects/?q=science'.format(
            API_BASE) in projects_link
        assert '/{}search/components/?q=science'.format(
            API_BASE) in components_link
        assert '/{}search/registrations/?q=science'.format(
            API_BASE) in registrations_link


class TestSearchComponents(ApiSearchTestCase):

    @pytest.fixture()
    def url_component_search(self):
        return '/{}search/components/'.format(API_BASE)

    def test_search_components(
            self, app, url_component_search, user, user_one, user_two,
            component, component_public, component_private):

        # test_search_public_component_no_auth
        res = app.get(url_component_search)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert component_public.title in res
        assert component.title in res

        # test_search_public_component_auth
        res = app.get(url_component_search, auth=user)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert component_public.title in res
        assert component.title in res

        # test_search_public_component_contributor
        res = app.get(url_component_search, auth=user_two)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert component_public.title in res
        assert component.title in res

        # test_search_private_component_no_auth
        res = app.get(url_component_search)
        assert res.status_code == 200
        assert component_private.title not in res

        # test_search_private_component_auth
        res = app.get(url_component_search, auth=user)
        assert res.status_code == 200
        assert component_private.title not in res

        # test_search_private_component_contributor
        res = app.get(url_component_search, auth=user_two)
        assert res.status_code == 200
        assert component_private.title not in res

        # test_search_component_by_title
        url = '{}?q={}'.format(url_component_search, 'beam')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert component_public.title == res.json['data'][0]['attributes']['title']

        # test_search_component_by_description
        url = '{}?q={}'.format(url_component_search, 'speak')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert component_public.title == res.json['data'][0]['attributes']['title']

        # test_search_component_by_tags
        url = '{}?q={}'.format(url_component_search, 'trumpets')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert component_public.title == res.json['data'][0]['attributes']['title']

        # test_search_component_by_contributor
        url = '{}?q={}'.format(url_component_search, 'Chance')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert component_public.title == res.json['data'][0]['attributes']['title']

        # test_search_component_no_results
        url = '{}?q={}'.format(url_component_search, 'Ocean')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 0
        assert total == 0

        # test_search_component_bad_query
        url = '{}?q={}'.format(
            url_component_search,
            'www.spam.com/help/twitter/')
        res = app.get(url, expect_errors=True)
        assert res.status_code == 400


class TestSearchFiles(ApiSearchTestCase):

    @pytest.fixture()
    def url_file_search(self):
        return '/{}search/files/'.format(API_BASE)

    def test_search_files(
            self, app, url_file_search, user, user_one,
            file_public, file_component, file_private):

        # test_search_public_file_no_auth
        res = app.get(url_file_search)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert file_public.name in res
        assert file_component.name in res

        # test_search_public_file_auth
        res = app.get(url_file_search, auth=user)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert file_public.name in res
        assert file_component.name in res

        # test_search_public_file_contributor
        res = app.get(url_file_search, auth=user_one)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert file_public.name in res
        assert file_component.name in res

        # test_search_private_file_no_auth
        res = app.get(url_file_search)
        assert res.status_code == 200
        assert file_private.name not in res

        # test_search_private_file_auth
        res = app.get(url_file_search, auth=user)
        assert res.status_code == 200
        assert file_private.name not in res

        # test_search_private_file_contributor
        res = app.get(url_file_search, auth=user_one)
        assert res.status_code == 200
        assert file_private.name not in res

        # test_search_file_by_name
        url = '{}?q={}'.format(url_file_search, 'highlights')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert file_component.name == res.json['data'][0]['attributes']['name']


class TestSearchProjects(ApiSearchTestCase):

    @pytest.fixture()
    def url_project_search(self):
        return '/{}search/projects/'.format(API_BASE)

    def test_search_projects(
            self, app, url_project_search, user, user_one,
            user_two, project, project_public, project_private):

        # test_search_public_project_no_auth
        res = app.get(url_project_search)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert project_public.title in res
        assert project.title in res

        # test_search_public_project_auth
        res = app.get(url_project_search, auth=user)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert project_public.title in res
        assert project.title in res

        # test_search_public_project_contributor
        res = app.get(url_project_search, auth=user_one)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert project_public.title in res
        assert project.title in res

        # test_search_private_project_no_auth
        res = app.get(url_project_search)
        assert res.status_code == 200
        assert project_private.title not in res

        # test_search_private_project_auth
        res = app.get(url_project_search, auth=user)
        assert res.status_code == 200
        assert project_private.title not in res

        # test_search_private_project_contributor
        res = app.get(url_project_search, auth=user_two)
        assert res.status_code == 200
        assert project_private.title not in res

        # test_search_project_by_title
        url = '{}?q={}'.format(url_project_search, 'pablo')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert project_public.title == res.json['data'][0]['attributes']['title']

        # test_search_project_by_description
        url = '{}?q={}'.format(url_project_search, 'genius')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert project_public.title == res.json['data'][0]['attributes']['title']

        # test_search_project_by_tags
        url = '{}?q={}'.format(url_project_search, 'Yeezus')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert project_public.title == res.json['data'][0]['attributes']['title']

        # test_search_project_by_contributor
        url = '{}?q={}'.format(url_project_search, 'kanye')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert project_public.title in res
        assert project.title in res

        # test_search_project_no_results
        url = '{}?q={}'.format(url_project_search, 'chicago')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 0
        assert total == 0

        # test_search_project_bad_query
        url = '{}?q={}'.format(
            url_project_search,
            'www.spam.com/help/facebook/')
        res = app.get(url, expect_errors=True)
        assert res.status_code == 400


@pytest.mark.django_db
class TestSearchRegistrations(ApiSearchTestCase):

    @pytest.fixture()
    def url_registration_search(self):
        return '/{}search/registrations/'.format(API_BASE)

    @pytest.fixture()
    def schema(self):
        schema = RegistrationSchema.objects.filter(
            name='Replication Recipe (Brandt et al., 2013): Post-Completion',
            schema_version=LATEST_SCHEMA_VERSION).first()
        return schema

    @pytest.fixture()
    def registration(self, project, schema):
        with mock_archive(project, autocomplete=True, autoapprove=True, schema=schema) as registration:
            return registration

    @pytest.fixture()
    def registration_public(self, project_public, schema):
        with mock_archive(project_public, autocomplete=True, autoapprove=True, schema=schema) as registration_public:
            return registration_public

    @pytest.fixture()
    def registration_private(self, project_private, schema):
        with mock_archive(project_private, autocomplete=True, autoapprove=True, schema=schema) as registration_private:
            registration_private.is_public = False
            registration_private.save()
            # TODO: This shouldn't be necessary, but tests fail if we don't do
            # this. Investigate further.
            registration_private.update_search()
            return registration_private

    def test_search_registrations(
            self, app, url_registration_search, user, user_one, user_two,
            registration, registration_public, registration_private):

        # test_search_public_registration_no_auth
        res = app.get(url_registration_search)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert registration_public.title in res
        assert registration.title in res

        # test_search_public_registration_auth
        res = app.get(url_registration_search, auth=user)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert registration_public.title in res
        assert registration.title in res

        # test_search_public_registration_contributor
        res = app.get(url_registration_search, auth=user_one)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert registration_public.title in res
        assert registration.title in res

        # test_search_private_registration_no_auth
        res = app.get(url_registration_search)
        assert res.status_code == 200
        assert registration_private.title not in res

        # test_search_private_registration_auth
        res = app.get(url_registration_search, auth=user)
        assert res.status_code == 200
        assert registration_private.title not in res

        # test_search_private_registration_contributor
        res = app.get(url_registration_search, auth=user_two)
        assert res.status_code == 200
        assert registration_private.title not in res

        # test_search_registration_by_title
        url = '{}?q={}'.format(url_registration_search, 'graduation')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert registration.title == res.json['data'][0]['attributes']['title']

        # test_search_registration_by_description
        url = '{}?q={}'.format(url_registration_search, 'crazy')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert registration_public.title == res.json['data'][0]['attributes']['title']

        # test_search_registration_by_tags
        url = '{}?q={}'.format(url_registration_search, 'yeezus')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert registration_public.title == res.json['data'][0]['attributes']['title']

        # test_search_registration_by_contributor
        url = '{}?q={}'.format(url_registration_search, 'west')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 2
        assert total == 2
        assert registration_public.title in res
        assert registration.title in res

        # test_search_registration_no_results
        url = '{}?q={}'.format(url_registration_search, '79th')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 0
        assert total == 0

        # test_search_registration_bad_query
        url = '{}?q={}'.format(
            url_registration_search,
            'www.spam.com/help/snapchat/')
        res = app.get(url, expect_errors=True)
        assert res.status_code == 400


class TestSearchUsers(ApiSearchTestCase):

    @pytest.fixture()
    def url_user_search(self):
        return '/{}search/users/'.format(API_BASE)

    def test_search_user(self, app, url_user_search, user, user_one, user_two):

        # test_search_users_no_auth
        res = app.get(url_user_search)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 3
        assert total == 3
        assert user.fullname in res

        # test_search_users_auth
        res = app.get(url_user_search, auth=user)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 3
        assert total == 3
        assert user.fullname in res

        # test_search_users_by_given_name
        url = '{}?q={}'.format(url_user_search, 'Kanye')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert user_one.given_name == res.json['data'][0]['attributes']['given_name']

        # test_search_users_by_middle_name
        url = '{}?q={}'.format(url_user_search, 'Omari')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert user_one.middle_names[0] == res.json['data'][0]['attributes']['middle_names'][0]

        # test_search_users_by_family_name
        url = '{}?q={}'.format(url_user_search, 'West')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert user_one.family_name == res.json['data'][0]['attributes']['family_name']

        # test_search_users_by_job
        url = '{}?q={}'.format(url_user_search, 'producer')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert user_one.fullname == res.json['data'][0]['attributes']['full_name']

        # test_search_users_by_school
        url = '{}?q={}'.format(url_user_search, 'Chicago')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert user_one.fullname == res.json['data'][0]['attributes']['full_name']


class TestSearchInstitutions(ApiSearchTestCase):

    @pytest.fixture()
    def url_institution_search(self):
        return '/{}search/institutions/'.format(API_BASE)

    def test_search_institutions(
            self, app, url_institution_search, user, institution):

        # test_search_institutions_no_auth
        res = app.get(url_institution_search)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert institution.name in res

        # test_search_institutions_auth
        res = app.get(url_institution_search, auth=user)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert institution.name in res

        # test_search_institutions_by_name
        url = '{}?q={}'.format(url_institution_search, 'Social')
        res = app.get(url)
        assert res.status_code == 200
        num_results = len(res.json['data'])
        total = res.json['links']['meta']['total']
        assert num_results == 1
        assert total == 1
        assert institution.name == res.json['data'][0]['attributes']['name']

class TestSearchCollections(ApiSearchTestCase):

    def get_ids(self, data):
        return [s['id'] for s in data]

    def post_payload(self, *args, **kwargs):
        return {
            'data': {
                'attributes': kwargs
            },
            'type': 'search'
        }

    @pytest.fixture()
    def url_collection_search(self):
        return '/{}search/collections/'.format(API_BASE)

    @pytest.fixture()
    def node_one(self, user):
        return NodeFactory(title='Ismael Lo: Tajabone', creator=user, is_public=True)

    @pytest.fixture()
    def registration_one(self, node_one):
        return RegistrationFactory(project=node_one, is_public=True)

    @pytest.fixture()
    def node_two(self, user):
        return NodeFactory(title='Sambolera', creator=user, is_public=True)

    @pytest.fixture()
    def registration_two(self, node_two):
        return RegistrationFactory(project=node_two, is_public=True)

    @pytest.fixture()
    def node_private(self, user):
        return NodeFactory(title='Classified', creator=user)

    @pytest.fixture()
    def registration_private(self, node_private):
        return RegistrationFactory(project=node_private, is_public=False)

    @pytest.fixture()
    def node_with_abstract(self, user):
        node_with_abstract = NodeFactory(title='Sambolera', creator=user, is_public=True)
        node_with_abstract.set_description(
            'Sambolera by Khadja Nin',
            auth=Auth(user),
            save=True)
        return node_with_abstract

    @pytest.fixture()
    def reg_with_abstract(self, node_with_abstract):
        return RegistrationFactory(project=node_with_abstract, is_public=True)

    def test_search_collections(
            self, app, url_collection_search, user, node_one, node_two, collection_public,
            node_with_abstract, node_private, registration_collection, registration_one, registration_two,
            registration_private, reg_with_abstract):

        collection_public.collect_object(node_one, user)
        collection_public.collect_object(node_two, user)
        collection_public.collect_object(node_private, user)

        registration_collection.collect_object(registration_one, user)
        registration_collection.collect_object(registration_two, user)
        registration_collection.collect_object(registration_private, user)

        # test_search_collections_no_auth
        res = app.get(url_collection_search)
        assert res.status_code == 200
        total = res.json['links']['meta']['total']
        num_results = len(res.json['data'])
        assert total == 4
        assert num_results == 4
        actual_ids = self.get_ids(res.json['data'])
        assert registration_private._id not in actual_ids
        assert node_private._id not in actual_ids

        # test_search_collections_auth
        res = app.get(url_collection_search, auth=user)
        assert res.status_code == 200
        total = res.json['links']['meta']['total']
        num_results = len(res.json['data'])
        assert total == 4
        assert num_results == 4
        actual_ids = self.get_ids(res.json['data'])
        assert registration_private._id not in actual_ids
        assert node_private._id not in actual_ids

        # test_search_collections_by_submission_title
        url = '{}?q={}'.format(url_collection_search, 'Ismael')
        res = app.get(url)
        assert res.status_code == 200
        total = res.json['links']['meta']['total']
        num_results = len(res.json['data'])
        assert node_one.title == registration_one.title == res.json['data'][0]['embeds']['guid']['data']['attributes']['title']
        assert total == num_results == 2

        # test_search_collections_by_submission_abstract
        collection_public.collect_object(node_with_abstract, user)
        registration_collection.collect_object(reg_with_abstract, user)
        url = '{}?q={}'.format(url_collection_search, 'KHADJA')
        res = app.get(url)
        assert res.status_code == 200
        total = res.json['links']['meta']['total']
        assert node_with_abstract.description == reg_with_abstract.description == res.json['data'][0]['embeds']['guid']['data']['attributes']['description']
        assert total == 2

        # test_search_collections_no_results:
        url = '{}?q={}'.format(url_collection_search, 'Wale Watu')
        res = app.get(url)
        assert res.status_code == 200
        total = res.json['links']['meta']['total']
        assert total == 0

    def test_POST_search_collections(
            self, app, url_collection_search, user, node_one, node_two, collection_public,
            node_with_abstract, node_private, registration_collection, registration_one,
            registration_two, registration_private, reg_with_abstract):
        collection_public.collect_object(node_one, user, status='asdf', issue='0', volume='1', program_area='asdf')
        collection_public.collect_object(node_two, user, collected_type='asdf', status='lkjh')
        collection_public.collect_object(node_with_abstract, user, status='asdf')
        collection_public.collect_object(node_private, user, status='asdf', collected_type='asdf')

        registration_collection.collect_object(registration_one, user, status='asdf')
        registration_collection.collect_object(registration_two, user, collected_type='asdf', status='lkjh')
        registration_collection.collect_object(reg_with_abstract, user, status='asdf')
        registration_collection.collect_object(registration_private, user, status='asdf', collected_type='asdf')

        # test_search_empty
        payload = self.post_payload()
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 6
        assert len(res.json['data']) == 6
        actual_ids = self.get_ids(res.json['data'])
        assert registration_private._id not in actual_ids
        assert node_private._id not in actual_ids

        # test_search_title_keyword
        payload = self.post_payload(q='Ismael')
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        assert len(res.json['data']) == 2
        actual_ids = self.get_ids(res.json['data'])
        assert registration_private._id not in actual_ids
        assert node_private._id not in actual_ids

        # test_search_abstract_keyword
        payload = self.post_payload(q='Khadja')
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        assert len(res.json['data']) == 2
        actual_ids = self.get_ids(res.json['data'])
        assert node_with_abstract._id in actual_ids
        assert reg_with_abstract._id in actual_ids

        # test_search_filter
        payload = self.post_payload(status='asdf')
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 4
        assert len(res.json['data']) == 4
        actual_ids = self.get_ids(res.json['data'])
        assert registration_private._id not in actual_ids
        assert node_private._id not in actual_ids

        payload = self.post_payload(status=['asdf', 'lkjh'])
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 6
        assert len(res.json['data']) == 6
        actual_ids = self.get_ids(res.json['data'])
        assert registration_private._id not in actual_ids
        assert node_private._id not in actual_ids

        payload = self.post_payload(collectedType='asdf')
        res = app.post_json_api(url_collection_search, payload)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        assert len(res.json['data']) == 2
        actual_ids = self.get_ids(res.json['data'])
        assert node_two._id in actual_ids
        assert registration_two._id in actual_ids

        payload = self.post_payload(status='asdf', issue='0', volume='1', programArea='asdf', collectedType='')
        res = app.post_json_api(url_collection_search, payload)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert len(res.json['data']) == 1
        actual_ids = self.get_ids(res.json['data'])
        assert node_one._id in actual_ids

        # test_search_abstract_keyword_and_filter
        payload = self.post_payload(q='Khadja', status='asdf')
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        assert len(res.json['data']) == 2
        actual_ids = self.get_ids(res.json['data'])
        assert node_with_abstract._id in actual_ids
        assert reg_with_abstract._id in actual_ids

        # test_search_abstract_keyword_and_filter_provider
        payload = self.post_payload(q='Khadja', status='asdf', provider=collection_public.provider._id)
        res = app.post_json_api(url_collection_search, payload)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == node_with_abstract._id
