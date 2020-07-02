import dateutil.relativedelta
from django.utils import timezone
import mock
from nose.tools import *  # noqa:
import pytest

from future.moves.urllib.parse import urljoin, urlparse

from api.base.settings.defaults import API_BASE
from api.base.versioning import CREATE_REGISTRATION_FIELD_CHANGE_VERSION
from api_tests.nodes.views.test_node_draft_registration_list import DraftRegistrationTestCase
from api_tests.subjects.mixins import SubjectsFilterMixin
from api_tests.registrations.filters.test_filters import RegistrationListFilteringMixin
from api_tests.utils import create_test_file
from framework.auth.core import Auth
from osf.models import RegistrationSchema, DraftRegistration
from osf_tests.factories import (
    EmbargoFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CollectionFactory,
    DraftRegistrationFactory,
    OSFGroupFactory,
    NodeLicenseRecordFactory,
    TagFactory,
    SubjectFactory,
    InstitutionFactory,
)
from osf_tests.management_commands.test_migration_registration_responses import prereg_registration_responses
from rest_framework import exceptions
from tests.base import ApiTestCase
from website import settings
from website.views import find_bookmark_collection
from website.project.metadata.schemas import from_json
from osf.utils import permissions

SCHEMA_VERSION = 2


@pytest.mark.enable_quickfiles_creation
class TestRegistrationList(ApiTestCase):

    def setUp(self):
        super(TestRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(
            creator=self.user, project=self.project)
        self.url = '/{}registrations/'.format(API_BASE)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(
            creator=self.user, project=self.public_project, is_public=True)
        self.user_two = AuthUserFactory()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert_equal(
            urlparse(url).path,
            '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        )

    def test_return_registrations_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.status_code, 200)

        registered_from_one = urlparse(
            res.json['data'][0]['relationships']['registered_from']['links']['related']['href']).path
        registered_from_two = urlparse(
            res.json['data'][1]['relationships']['registered_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert [registered_from_one, registered_from_two] == ['/{}nodes/{}/'.format(API_BASE, self.public_project._id),
             '/{}nodes/{}/'.format(API_BASE, self.project._id)]

    def test_return_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        registered_from = urlparse(
            res.json['data'][0]['relationships']['registered_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_equal(
            registered_from,
            '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_total_biographic_contributor_in_registration(self):
        user3 = AuthUserFactory()
        registration = RegistrationFactory(is_public=True, creator=self.user)
        registration.add_contributor(self.user_two, auth=Auth(self.user))
        registration.add_contributor(
            user3, auth=Auth(self.user), visible=False)
        registration.save()
        registration_url = '/{0}registrations/{1}/?embed=contributors'.format(
            API_BASE, registration._id)

        res = self.app.get(registration_url)
        assert_true(
            res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic']
        )
        assert_equal(
            res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic'], 2
        )

    def test_exclude_nodes_from_registrations_endpoint(self):
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.registration_project._id, ids)
        assert_in(self.public_registration_project._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.project._id, ids)

@pytest.mark.enable_quickfiles_creation
class TestSparseRegistrationList(ApiTestCase):

    def setUp(self):
        super(TestSparseRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(
            creator=self.user, project=self.project)
        self.url = '/{}sparse/registrations/'.format(API_BASE)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(
            creator=self.user, project=self.public_project, is_public=True)
        self.user_two = AuthUserFactory()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert 'registered_from' not in res.json['data'][0]['relationships']

    def test_return_registrations_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.status_code, 200)
        assert 'registered_from' not in res.json['data'][0]['relationships']
        assert 'registered_from' not in res.json['data'][1]['relationships']
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert 'registered_from' not in res.json['data'][0]['relationships']
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_total_biographic_contributor_in_registration(self):
        user3 = AuthUserFactory()
        registration = RegistrationFactory(is_public=True, creator=self.user)
        registration.add_contributor(self.user_two, auth=Auth(self.user))
        registration.add_contributor(
            user3, auth=Auth(self.user), visible=False)
        registration.save()
        registration_url = '/{0}registrations/{1}/?embed=contributors'.format(
            API_BASE, registration._id)

        res = self.app.get(registration_url)
        assert_true(
            res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic']
        )
        assert_equal(
            res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic'], 2
        )

    def test_exclude_nodes_from_registrations_endpoint(self):
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.registration_project._id, ids)
        assert_in(self.public_registration_project._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.project._id, ids)


@pytest.mark.enable_bookmark_creation
class TestRegistrationFiltering(ApiTestCase):

    def setUp(self):
        super(TestRegistrationFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(
            title='Project One',
            description='Two',
            is_public=True,
            creator=self.user_one,
            category='hypothesis')
        self.project_two = ProjectFactory(
            title='Project Two',
            description='One Three',
            is_public=True,
            creator=self.user_one)
        self.project_three = ProjectFactory(
            title='Three',
            description='',
            is_public=True,
            creator=self.user_two
        )

        self.private_project_user_one = ProjectFactory(
            title='Private Project User One', is_public=False, creator=self.user_one, description='')
        self.private_project_user_two = ProjectFactory(
            title='Private Project User Two', is_public=False, creator=self.user_two, description='')

        self.project_one.add_tag('tag1', Auth(
            self.project_one.creator), save=False)
        self.project_one.add_tag('tag2', Auth(
            self.project_one.creator), save=False)
        self.project_one.save()
        self.project_two.add_tag('tag1', Auth(
            self.project_two.creator), save=True)
        self.project_two.save()

        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True)
        self.project_two_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_two, is_public=True)
        self.project_three_reg = RegistrationFactory(
            creator=self.user_two, project=self.project_three, is_public=True, title='No search terms!')
        self.private_project_user_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.private_project_user_one, is_public=False, title='No search terms!')
        self.private_project_user_two_reg = RegistrationFactory(
            creator=self.user_two, project=self.private_project_user_two, is_public=False, title='No search terms!')

        self.folder = CollectionFactory()
        self.bookmark_collection = find_bookmark_collection(self.user_one)

        self.url = '/{}registrations/'.format(API_BASE)

    def test_filtering_by_category(self):
        url = '/{}registrations/?filter[category]=hypothesis'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        registration_json = res.json['data']
        ids = [each['id'] for each in registration_json]

        assert_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

    def test_filtering_by_public(self):
        url = '/{}registrations/?filter[public]=false'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        reg_json = res.json['data']

        # No public projects returned
        assert_false(
            any([each['attributes']['public'] for each in reg_json])
        )

        ids = [each['id'] for each in reg_json]
        assert_not_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)

        url = '/{}registrations/?filter[public]=true'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        reg_json = res.json['data']

        # No private projects returned
        assert_true(
            all([each['attributes']['public'] for each in reg_json])
        )

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

    def test_filtering_tags(self):

        # both project_one and project_two have tag1
        url = '/{}registrations/?filter[tags]={}'.format(API_BASE, 'tag1')

        res = self.app.get(url, auth=self.project_one.creator.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        # filtering two tags
        # project_one has both tags; project_two only has one
        url = '/{}registrations/?filter[tags]={}&filter[tags]={}'.format(
            API_BASE, 'tag1', 'tag2')

        res = self.app.get(url, auth=self.project_one.creator.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

    def test_filtering_tags_exact(self):
        self.project_one.add_tag('cats', Auth(self.user_one))
        self.project_two.add_tag('cats', Auth(self.user_one))
        self.project_one.add_tag('cat', Auth(self.user_one))
        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True)
        self.project_two_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_two, is_public=True)
        res = self.app.get(
            '/{}registrations/?filter[tags]=cat'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 1)

    def test_filtering_tags_capitalized_query(self):
        self.project_one.add_tag('cat', Auth(self.user_one))
        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True)
        res = self.app.get(
            '/{}registrations/?filter[tags]=CAT'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 1)

    def test_filtering_tags_capitalized_tag(self):
        self.project_one.add_tag('CAT', Auth(self.user_one))
        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True)
        res = self.app.get(
            '/{}registrations/?filter[tags]=cat'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 1)

    def test_filtering_on_multiple_tags(self):
        self.project_one.add_tag('cat', Auth(self.user_one))
        self.project_one.add_tag('sand', Auth(self.user_one))
        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True)
        res = self.app.get(
            '/{}registrations/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 1)

    def test_filtering_on_multiple_tags_must_match_both(self):
        self.project_one.add_tag('cat', Auth(self.user_one))
        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True)
        res = self.app.get(
            '/{}registrations/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 0)

    def test_filtering_tags_returns_distinct(self):
        # regression test for returning multiple of the same file
        self.project_one.add_tag('cat', Auth(self.user_one))
        self.project_one.add_tag('cAt', Auth(self.user_one))
        self.project_one.add_tag('caT', Auth(self.user_one))
        self.project_one.add_tag('CAT', Auth(self.user_one))
        self.project_one_reg = RegistrationFactory(
            creator=self.user_one, project=self.project_one, is_public=True, title='No search terms!')
        res = self.app.get(
            '/{}registrations/?filter[tags]=cat'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 1)

    def test_filtering_contributors(self):
        res = self.app.get(
            '/{}registrations/?filter[contributors]={}'.format(
                API_BASE, self.user_one._id
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 3)

    def test_filtering_contributors_bad_id(self):
        res = self.app.get(
            '/{}registrations/?filter[contributors]=acatdresseduplikeahuman'.format(
                API_BASE
            ),
            auth=self.user_one.auth
        )
        assert_equal(len(res.json.get('data')), 0)

    def test_get_all_registrations_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_in(self.project_three_reg._id, ids)
        assert_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_all_registrations_with_no_filter_not_logged_in(self):
        res = self.app.get(self.url)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_one_registration_with_exact_filter_logged_in(self):
        url = '/{}registrations/?filter[title]=Project%20One'.format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_one_registration_with_exact_filter_not_logged_in(self):
        url = '/{}registrations/?filter[title]=Private%20Project%20User%20One'.format(
            API_BASE)

        res = self.app.get(url)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_not_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_some_registrations_with_substring_logged_in(self):
        url = '/{}registrations/?filter[title]=Two'.format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_not_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_some_registrations_with_substring_not_logged_in(self):
        url = '/{}registrations/?filter[title]=One'.format(API_BASE)

        res = self.app.get(url)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_only_public_or_my_registrations_with_filter_logged_in(self):
        url = '/{}registrations/?filter[title]=Project'.format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_only_public_registrations_with_filter_not_logged_in(self):
        url = '/{}registrations/?filter[title]=Project'.format(API_BASE)

        res = self.app.get(url)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_alternate_filtering_field_logged_in(self):
        url = '/{}registrations/?filter[description]=Three'.format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_not_in(self.project_one_reg._id, ids)
        assert_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_alternate_filtering_field_not_logged_in(self):
        url = '/{}registrations/?filter[description]=Two'.format(API_BASE)

        res = self.app.get(url)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_incorrect_filtering_field_not_logged_in(self):
        url = '/{}registrations/?filter[notafield]=bogus'.format(API_BASE)

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(
            errors[0]['detail'],
            "'notafield' is not a valid field for this endpoint.")


class TestRegistrationSubjectFiltering(SubjectsFilterMixin):
    @pytest.fixture()
    def resource(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def resource_two(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def url(self):
        return '/{}registrations/'.format(API_BASE)


class TestNodeRegistrationCreate(DraftRegistrationTestCase):
    """
    Tests for creating registration through old workflow -
    POST NodeRegistrationList
    """

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='Replication Recipe (Brandt et al., 2013): Post-Completion',
            schema_version=SCHEMA_VERSION)

    @pytest.fixture()
    def project_public_child(self, project_public):
        return ProjectFactory(parent=project_public)

    @pytest.fixture()
    def project_public_grandchild(self, project_public_child):
        return ProjectFactory(parent=project_public_child)

    @pytest.fixture()
    def project_public_excluded_sibling(self, project_public):
        return ProjectFactory(parent=project_public)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public,
            registration_metadata={
                'item29': {'value': 'Yes'},
                'item33': {'value': 'success'}
            }
        )

    @pytest.fixture()
    def url_registrations(self, project_public):
        return '/{}nodes/{}/registrations/'.format(
            API_BASE, project_public._id)

    @pytest.fixture()
    def url_registrations_ver(self, project_public, url_registrations):
        return '{}?version={}'.format(url_registrations, CREATE_REGISTRATION_FIELD_CHANGE_VERSION)

    @pytest.fixture()
    def payload(self, draft_registration):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'immediate'
                }
            }
        }

    @pytest.fixture()
    def payload_with_children(self, draft_registration, project_public_child, project_public_grandchild):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'children': [project_public_child._id, project_public_grandchild._id],
                    'registration_choice': 'immediate'

                }
            }
        }

    @pytest.fixture()
    def payload_with_grandchildren_but_no_children(self, draft_registration, project_public_child, project_public_grandchild):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'children': [project_public_grandchild._id],
                    'registration_choice': 'immediate'

                }
            }
        }

    @pytest.fixture()
    def payload_with_bad_child_node_guid(self, draft_registration):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'children': ['fake0', 'fake3'],
                    'registration_choice': 'immediate'

                }
            }
        }

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_admin_can_create_registration(
            self, mock_enqueue, app, user, payload, url_registrations):
        res = app.post_json_api(url_registrations, payload, auth=user.auth)
        data = res.json['data']['attributes']
        assert res.status_code == 201
        assert data['registration'] is True
        assert data['pending_registration_approval'] is True
        assert data['registration_responses'] == {
            'item32': '',
            'item33': 'success',
            'item30': '',
            'item31': '',
            'item36': '',
            'item37': '',
            'item34': '',
            'item35': '',
            'item29': 'Yes'
        }
        assert data['public'] is False

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_draft_registration_retains_editable_fields_after_reg(
            self, mock_enqueue, app, user, payload, url_registrations, draft_registration):
        draft_registration.title = 'draft reg title'
        draft_registration.description = 'Life Moves Pretty fast'
        draft_registration.category = 'hypothesis'
        node_license_rec = NodeLicenseRecordFactory()
        draft_registration.node_license = node_license_rec
        new_tag = TagFactory()
        draft_registration.tags.add(new_tag)
        new_subject = SubjectFactory()
        draft_registration.subjects.add(new_subject)
        new_institution = InstitutionFactory()
        draft_registration.affiliated_institutions.add(new_institution)
        draft_registration.save()

        res = app.post_json_api(url_registrations, payload, auth=user.auth)
        data = res.json['data']
        attributes = data['attributes']
        assert res.status_code == 201
        assert attributes['registration'] is True
        assert attributes['pending_registration_approval'] is True
        assert attributes['title'] == 'draft reg title'
        assert attributes['description'] == 'Life Moves Pretty fast'
        assert attributes['category'] == 'hypothesis'
        assert attributes['node_license']['copyright_holders'] == node_license_rec.copyright_holders
        assert attributes['node_license']['year'] == node_license_rec.year
        assert new_tag.name in attributes['tags']

        registration_id = data['id']

        subjects_url = f'/{API_BASE}registrations/{registration_id}/subjects/'
        institutions_url = f'/{API_BASE}registrations/{registration_id}/institutions/'

        res = app.get(subjects_url, auth=user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert data[0]['id'] == new_subject._id

        res = app.get(institutions_url, auth=user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert data[0]['id'] == new_institution._id

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_admin_can_create_registration_with_specific_children(
            self, mock_enqueue, app, user, payload_with_children, project_public, project_public_child, project_public_excluded_sibling, project_public_grandchild, url_registrations):
        res = app.post_json_api(url_registrations, payload_with_children, auth=user.auth)
        data = res.json['data']['attributes']
        assert res.status_code == 201
        assert data['registration'] is True
        assert data['pending_registration_approval'] is True
        assert data['public'] is False

        assert project_public.registrations.all().count() == 1
        assert project_public_child.registrations.all().count() == 1
        assert project_public_grandchild.registrations.all().count() == 1
        assert project_public_excluded_sibling.registrations.all().count() == 0

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_admin_400_with_bad_child_node_guid(
            self, mock_enqueue, app, user, payload_with_bad_child_node_guid, url_registrations):
        res = app.post_json_api(url_registrations, payload_with_bad_child_node_guid, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Some child nodes could not be found.'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_admin_cant_register_grandchildren_without_children(
            self, mock_enqueue, app, user, payload_with_grandchildren_but_no_children, url_registrations, project_public_grandchild):
        res = app.post_json_api(url_registrations, payload_with_grandchildren_but_no_children, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The parents of all child nodes being registered must be registered.'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_old_workflow_node_editable_metadata_copied(
            self, mock_enqueue, app, user, url_registrations, payload, project_public, draft_registration):
        # Ensure that modifying the parent project for the draft registration doesn't affect the title of the draft reg
        project_public.title = 'Recently updated title'
        project_public.save()
        res = app.post_json_api(url_registrations, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 201
        # Assert project updates are transferred to registration, trumping draft registration fields
        assert res.json['data']['attributes']['title'] != 'Recently updated title'

    def test_cannot_create_registration(
            self, app, user_write_contrib, user_read_contrib,
            payload, url_registrations, project_public):

        # def test_write_only_contributor_cannot_create_registration(self):
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    # def test_read_only_contributor_cannot_create_registration(self):
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    # def test_non_authenticated_user_cannot_create_registration(self):
        res = app.post_json_api(url_registrations, payload, expect_errors=True)
        assert res.status_code == 401

        # admin via a group cannot create registration
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        project_public.add_osf_group(group, permissions.ADMIN)
        res = app.post_json_api(url_registrations, payload, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 403

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_registration_draft_must_be_specified(
            self, mock_enqueue, app, user, payload, url_registrations):
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'registration_choice': 'immediate'
                }
            }
        }
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert '/data/attributes/draft_registration' in res.json['errors'][0]['source']['pointer']
        assert res.json['errors'][0]['detail'] == 'This field is required.'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_registration_draft_must_be_valid(
            self, mock_enqueue, app, user, url_registrations):
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'registration_choice': 'immediate',
                    'draft_registration': '12345',

                }
            }
        }
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_registration_draft_must_be_draft_of_current_node(
            self, mock_enqueue, app, user, schema, url_registrations):
        project_new = ProjectFactory(creator=user)
        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_new,
            registration_metadata={
                'item29': {'value': 'Yes'},
                'item33': {'value': 'success'}
            }
        )
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'registration_choice': 'immediate',
                    'draft_registration': draft_registration._id,
                }
            }
        }
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This draft registration is not created from the given node.'

    @pytest.mark.skip('TEMPORARY: Unskip when JSON Schemas are updated')
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_required_top_level_questions_must_be_answered_on_draft(
            self, mock_enqueue, app, user, project_public,
            metadata, url_registrations):

        test_schema = from_json('prereg-prize.json')
        schema = RegistrationSchema.objects.get(
            name='Test Schema',
            schema=test_schema,
            schema_version=SCHEMA_VERSION
        )

        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

        registration_metadata = metadata(draft_registration)
        del registration_metadata['q1']
        draft_registration.registration_metadata = registration_metadata
        draft_registration.save()

        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'registration_choice': 'immediate',
                    'draft_registration': draft_registration._id,
                }
            }
        }

        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration the \'Title\' field is required'

    @pytest.mark.skip('TEMPORARY: Unskip when JSON Schemas are updated')
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_required_second_level_questions_must_be_answered_on_draft(
            self, mock_enqueue, app, user, project_public, metadata, url_registrations):

        test_schema = from_json('prereg-prize.json')
        schema = RegistrationSchema.objects.get(
            name='Test Schema',
            schema=test_schema,
            schema_version=SCHEMA_VERSION
        )

        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

        registration_metadata = metadata(draft_registration)
        registration_metadata['q11'] = {'value': {}}
        draft_registration.registration_metadata = registration_metadata
        draft_registration.save()

        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'registration_choice': 'immediate',
                    'draft_registration': draft_registration._id,
                }
            }
        }

        res = app.post_json_api(
            url_registrations, payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Manipulated variables\' field is invalid.'

    @pytest.mark.skip('TEMPORARY: Unskip when JSON Schemas are updated')
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_required_third_level_questions_must_be_answered_on_draft(
            self, mock_enqueue, app, user, project_public, metadata, url_registrations):

        test_schema = from_json('prereg-prize.json')
        schema = RegistrationSchema.objects.get(
            name='Test Schema',
            schema=test_schema,
            schema_version=SCHEMA_VERSION
        )

        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

        registration_metadata = metadata(draft_registration)
        registration_metadata['q11'] = {'value': {'question': {}}}

        draft_registration.registration_metadata = registration_metadata
        draft_registration.save()

        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'registration_choice': 'immediate',
                    'draft_registration': draft_registration._id,
                }
            }
        }

        res = app.post_json_api(
            url_registrations, payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'For your registration your response to the \'Manipulated variables\' field is invalid.'

    @pytest.mark.skip('TEMPORARY: Unskip when JSON Schemas are updated')
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_multiple_choice_in_registration_schema_must_match_one_of_choices(
            self, mock_enqueue, app, user, project_public, schema, payload, url_registrations):
        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public,
            registration_metadata={
                'item29': {'value': 'Yes'},
                'item33': {'value': 'success!'}
            }
        )
        payload['data']['attributes']['draft_registration'] = draft_registration._id
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert (
            res.json['errors'][0]['detail'] == 'For your registration your response to the \'I judge the replication to be a(n)\''
                                               ' field is invalid, your response must be one of the provided options.')

    def test_invalid_registration_choice(
            self, app, user, draft_registration, url_registrations):
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'tomorrow'
                }
            }
        }
        res = app.post_json_api(
            url_registrations, payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/registration_choice'
        assert res.json['errors'][0]['detail'] == '"tomorrow" is not a valid choice.'

        @mock.patch('framework.celery_tasks.handlers.enqueue_task')
        def test_embargo_end_date_provided_if_registration_choice_is_embargo(
                self, mock_enqueue, app, user, draft_registration, url_registrations):
            payload = {
                'data': {
                    'type': 'registrations',
                    'attributes': {
                        'draft_registration': draft_registration._id,
                        'registration_choice': 'embargo'
                    }
                }
            }

            res = app.post_json_api(
                url_registrations,
                payload,
                auth=user.auth,
                expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'lift_embargo must be specified.'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_embargo_must_be_less_than_four_years(
            self, mock_enqueue, app, user, draft_registration,
            url_registrations):
        today = timezone.now()
        five_years = (
            today +
            dateutil.relativedelta.relativedelta(
                years=5)).strftime('%Y-%m-%dT%H:%M:%S')
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'embargo',
                    'lift_embargo': five_years,
                }
            }
        }

        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registrations can only be embargoed for up to four years.'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_embargo_registration(
            self, mock_enqueue, app, user,
            draft_registration, url_registrations):
        today = timezone.now()
        next_week = (
            today +
            dateutil.relativedelta.relativedelta(
                months=1)).strftime('%Y-%m-%dT%H:%M:%S')
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'embargo',
                    'lift_embargo': next_week,
                }
            }
        }

        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 201
        data = res.json['data']['attributes']
        assert data['registration'] is True
        assert data['pending_embargo_approval'] is True

    def test_embargo_end_date_must_be_in_the_future(
            self, app, user, draft_registration, url_registrations):
        today = timezone.now().strftime('%Y-%m-%dT%H:%M:%S')
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'embargo',
                    'lift_embargo': today,
                }
            }
        }

        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Embargo end date must be at least three days in the future.'

    def test_invalid_embargo_end_date_format(
            self, app, user, draft_registration, url_registrations):
        today = timezone.now().isoformat()
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'embargo',
                    'lift_embargo': today,
                }
            }
        }

        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm:ss.'

    def test_new_API_version_requires_draft_registration_id_on_creation(
            self, app, user, draft_registration, url_registrations_ver):
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                }
            }
        }
        res = app.post_json_api(
            url_registrations_ver,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/draft_registration_id'
        assert res.json['errors'][0]['detail'] == 'This field is required.'

    def test_new_API_version_no_embargo_is_immediate_by_default(
            self, app, user, draft_registration, url_registrations_ver):
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration_id': draft_registration._id,
                }
            }
        }
        res = app.post_json_api(
            url_registrations_ver,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 201
        assert res.json['data']['attributes']['pending_registration_approval'] is True

    def test_new_API_version_uses_embargo_end_date(
            self, app, user, draft_registration, url_registrations_ver):
        today = timezone.now()
        three_years = (
            today +
            dateutil.relativedelta.relativedelta(
                years=3)).strftime('%Y-%m-%dT%H:%M:%S')

        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration_id': draft_registration._id,
                    'embargo_end_date': three_years
                }
            }
        }
        res = app.post_json_api(
            url_registrations_ver,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 201
        assert res.json['data']['attributes']['pending_embargo_approval'] is True

    def test_new_API_version_errors_on_lift_embargo(
            self, app, user, draft_registration, url_registrations_ver):
        today = timezone.now()
        three_years = (
            today +
            dateutil.relativedelta.relativedelta(
                years=3)).strftime('%Y-%m-%dT%H:%M:%S')

        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration_id': draft_registration._id,
                    'lift_embargo': three_years
                }
            }
        }
        res = app.post_json_api(
            url_registrations_ver,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert (res.json['errors'][0]['detail'] ==
            f'Deprecated in version {CREATE_REGISTRATION_FIELD_CHANGE_VERSION}. Use embargo_end_date instead.')
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/lift_embargo'

    def test_new_API_version_errors_on_registration_choice(
            self, app, user, draft_registration, url_registrations_ver):
        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration_id': draft_registration._id,
                    'registration_choice': 'embargo'
                }
            }
        }
        res = app.post_json_api(
            url_registrations_ver,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert (res.json['errors'][0]['detail'] ==
            f'Deprecated in version {CREATE_REGISTRATION_FIELD_CHANGE_VERSION}. Use embargo_end_date instead.')
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/registration_choice'

    def test_new_API_version_uses_included_node_ids_instead_of_children(
            self, app, user, draft_registration, url_registrations_ver, project_public,
            project_public_child, project_public_grandchild, project_public_excluded_sibling):
        payload_with_children = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration_id': draft_registration._id,
                    'included_node_ids': [project_public_child._id, project_public_grandchild._id],

                }
            }
        }
        res = app.post_json_api(
            url_registrations_ver,
            payload_with_children,
            auth=user.auth)
        data = res.json['data']['attributes']
        assert res.status_code == 201
        assert data['registration'] is True
        assert data['pending_registration_approval'] is True
        assert data['public'] is False

        assert project_public.registrations.all().count() == 1
        assert project_public_child.registrations.all().count() == 1
        assert project_public_grandchild.registrations.all().count() == 1
        assert project_public_excluded_sibling.registrations.all().count() == 0

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_cannot_register_draft_that_has_already_been_registered(
            self, mock_enqueue, app, user, payload, draft_registration, url_registrations):
        draft_registration.register(auth=Auth(user), save=True)
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'This draft has already been registered and cannot be modified.'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_cannot_register_draft_that_is_pending_review(
            self, mock_enqueue, app, user, payload, url_registrations):
        with mock.patch.object(DraftRegistration, 'is_pending_review', mock.PropertyMock(return_value=True)):
            res = app.post_json_api(
                url_registrations,
                payload,
                auth=user.auth,
                expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'This draft is pending review and cannot be modified.'

    def test_cannot_register_draft_that_has_already_been_approved(
            self, app, user, payload, url_registrations):
        with mock.patch.object(DraftRegistration, 'requires_approval', mock.PropertyMock(return_value=True)), mock.patch.object(DraftRegistration, 'is_approved', mock.PropertyMock(return_value=True)):
            res = app.post_json_api(
                url_registrations,
                payload,
                auth=user.auth,
                expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'This draft has already been approved and cannot be modified.'

    def test_cannot_register_draft_that_has_orphan_files(
            self, app, user, payload, draft_registration, url_registrations):
        schema = draft_registration.registration_schema
        schema.schema['pages'][0]['questions'][0].update({
            u'description': u'Upload files!',
            u'format': u'osf-upload-open',
            u'qid': u'qwhatever',
            u'title': u'Upload an analysis script with clear comments',
            u'type': u'osf-upload',
        })
        schema.save()

        draft_registration.registration_metadata = {
            'qwhatever': {
                'value': 'file 1',
                'extra': [{
                    'nodeId': 'badid',
                    'selectedFileName': 'file 1',
                }]
            }
        }
        draft_registration.save()
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'All files attached to this form must be registered to complete the' \
                                                  ' process. The following file(s) are attached, but are not part of' \
                                                  ' a component being registered: file 1'

    def test_assert_file_validity_on_registration_metadata(
        self, app, user, payload, url_registrations, project_public
    ):
        file_name = 'registration_file.pdf'
        sha256 = 'asdfjkl'
        file = create_test_file(project_public, user, file_name)
        version = file.versions.first()
        # mock sha256
        version.metadata['sha256'] = sha256
        version.save()

        prereg_schema = RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)

        prereg_draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=prereg_schema,
            branched_from=project_public
        )

        prereg_registration_responses['q11.uploader'] = []

        # q7 has file information
        prereg_draft_registration.update_registration_responses(prereg_registration_responses)
        prereg_draft_registration.save()

        prereg_draft_registration.save()

        payload = {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': prereg_draft_registration._id,
                    'registration_choice': 'immediate',
                }
            }
        }

        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        # File with the given name in the payload doesn't exist on the node
        assert res.status_code == 400

        file_view_url = urljoin(settings.DOMAIN, '/project/{}/files/osfstorage/{}'.format(
            prereg_draft_registration.branched_from._id,
            file._id,
        ))
        prereg_registration_responses['q7.uploader'] = [{
            'file_name': file_name,
            'file_id': file._id,
            'file_hashes': {
                'sha256': 'incorrect_sha',
            },
            'file_urls': {
                'html': file_view_url,
            },
        }]

        prereg_draft_registration.update_registration_responses(prereg_registration_responses)
        prereg_draft_registration.save()
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        # sha256 is inaccurate
        assert res.status_code == 400

        prereg_registration_responses['q7.uploader'] = [{
            'file_name': file_name,
            'file_id': file._id,
            'file_hashes': {
                'sha256': sha256,
            },
            'file_urls': {
                'html': file_view_url,
            },
        }]

        prereg_draft_registration.update_registration_responses(prereg_registration_responses)
        prereg_draft_registration.save()
        res = app.post_json_api(
            url_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 201

class TestRegistrationCreate(TestNodeRegistrationCreate):
    """
    Tests for creating registration through new workflow -
    POST RegistrationList
    """

    @pytest.fixture()
    def url_registrations(self, project_public):
        return '/{}registrations/'.format(
            API_BASE
        )

    @pytest.fixture()
    def url_registrations_ver(self, project_public):
        return '/{}registrations/?version={}'.format(
            API_BASE,
            CREATE_REGISTRATION_FIELD_CHANGE_VERSION
        )

    @pytest.fixture()
    def payload(self, draft_registration):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'registration_choice': 'immediate'
                }
            }
        }

    @pytest.fixture()
    def payload_ver(self, draft_registration):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration_id': draft_registration._id
                }
            }
        }

    @pytest.fixture()
    def payload_with_children(self, draft_registration, project_public_child, project_public_grandchild):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'children': [project_public_child._id, project_public_grandchild._id],
                    'registration_choice': 'immediate'
                }
            }
        }

    @pytest.fixture()
    def payload_with_grandchildren_but_no_children(self, draft_registration, project_public_child, project_public_grandchild):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'children': [project_public_grandchild._id],
                    'registration_choice': 'immediate'

                }
            }
        }

    @pytest.fixture()
    def payload_with_bad_child_node_guid(self, draft_registration):
        return {
            'data': {
                'type': 'registrations',
                'attributes': {
                    'draft_registration': draft_registration._id,
                    'children': ['fake0', 'fake3'],
                    'registration_choice': 'immediate'
                }
            }
        }

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_registration_draft_must_be_draft_of_current_node(
            self, mock_enqueue, app, user, schema, url_registrations_ver):
        # Overrides TestNodeRegistrationCreate - node is not in URL in this workflow
        return

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_need_admin_perms_on_node_and_draft(
            self, mock_enqueue, app, user, payload_ver, url_registrations_ver):
        user_two = AuthUserFactory()
        group = OSFGroupFactory(creator=user)

        draft_registration = DraftRegistrationFactory(creator=user_two)
        draft_registration.add_contributor(user, permissions.ADMIN)
        draft_registration.branched_from.add_contributor(user, permissions.WRITE)
        payload_ver['data']['attributes']['draft_registration_id'] = draft_registration._id
        # User is admin on draft, but not on node
        assert draft_registration.branched_from.is_admin_contributor(user) is False
        assert draft_registration.has_permission(user, permissions.ADMIN) is True
        res = app.post_json_api(url_registrations_ver, payload_ver, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You must be an admin contributor on both the project and the draft registration to create a registration.'

        # User is an admin group contributor on the node (not enough)
        draft_registration.branched_from.add_osf_group(group, permissions.ADMIN)
        payload_ver['data']['attributes']['draft_registration_id'] = draft_registration._id
        assert draft_registration.branched_from.is_admin_contributor(user) is False
        assert draft_registration.branched_from.has_permission(user, permissions.ADMIN) is True
        assert draft_registration.has_permission(user, permissions.ADMIN) is True
        res = app.post_json_api(url_registrations_ver, payload_ver, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You must be an admin contributor on both the project and the draft registration to create a registration.'

        draft_registration = DraftRegistrationFactory(creator=user_two)
        draft_registration.add_contributor(user, permissions.WRITE)
        draft_registration.branched_from.add_contributor(user, permissions.ADMIN)
        payload_ver['data']['attributes']['draft_registration_id'] = draft_registration._id
        # User is admin on node but not on draft
        draft_registration.branched_from.is_admin_contributor(user) is True
        assert draft_registration.has_permission(user, permissions.ADMIN) is False
        res = app.post_json_api(url_registrations_ver, payload_ver, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You must be an admin contributor on both the project and the draft registration to create a registration.'

        # User is admin on draft and node
        draft_registration = DraftRegistrationFactory(creator=user)
        assert draft_registration.branched_from.is_admin_contributor(user) is True
        assert draft_registration.has_permission(user, permissions.ADMIN) is True
        payload_ver['data']['attributes']['draft_registration_id'] = draft_registration._id
        res = app.post_json_api(url_registrations_ver, payload_ver, auth=user.auth)
        assert res.status_code == 201

    def test_invalid_registration_choice(self):
        # Overrides TestNodeRegistrationCreate - this isn't a field used here
        pass

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_old_workflow_node_editable_metadata_copied(
            self, mock_enqueue, app, user, url_registrations_ver, payload_ver, project_public, draft_registration):
        # Overrides TestNodeRegistrationCreate - new workflow (POST to /v2/registrations/) does
        # not copy fields

        # New workflow allows you to edit fields on draft registration, but old workflow does not.
        project_public.title = 'Recently updated title'
        project_public.save()
        res = app.post_json_api(url_registrations_ver, payload_ver, auth=user.auth, expect_errors=True)
        assert res.status_code == 201
        # Draft Registration fields trump nodes fields in new workflow.  Project's title
        # is not transferred to the reg, the draft's is.
        assert res.json['data']['attributes']['title'] != 'Recently updated title'

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_draft_registration_title_enforced(
            self, mock_enqueue, app, user, url_registrations_ver, payload_ver, draft_registration):

        draft_registration.title = ''
        draft_registration.save()
        res = app.post_json_api(url_registrations_ver, payload_ver, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Draft Registration must have title to be registered'


@pytest.mark.django_db
class TestRegistrationBulkUpdate:

    @pytest.fixture()
    def url(self):
        return '/{}registrations/'.format(API_BASE)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration_one(self, user):
        return RegistrationFactory(
            creator=user,
            title='Birds',
            embargo=EmbargoFactory(
                user=user),
            is_public=False)

    @pytest.fixture()
    def registration_two(self, user):
        return RegistrationFactory(
            creator=user,
            title='Birds II',
            embargo=EmbargoFactory(
                user=user),
            is_public=False)

    @pytest.fixture()
    def private_payload(self, registration_one, registration_two):
        return {
            'data': [
                {
                    'id': registration_one._id,
                    'type': 'registrations',
                    'attributes': {
                        'public': False
                    }
                },
                {
                    'id': registration_two._id,
                    'type': 'registrations',
                    'attributes': {
                        'public': False
                    }
                }
            ]
        }

    @pytest.fixture()
    def public_payload(self, registration_one, registration_two):
        return {
            'data': [
                {
                    'id': registration_one._id,
                    'type': 'registrations',
                    'attributes': {
                        'public': True
                    }
                },
                {
                    'id': registration_two._id,
                    'type': 'registrations',
                    'attributes': {
                        'public': True
                    }
                }
            ]
        }

    @pytest.fixture()
    def empty_payload(self, registration_one, registration_two):
        return {
            'data': [
                {
                    'id': registration_one._id,
                    'type': 'registrations',
                    'attributes': {}
                },
                {
                    'id': registration_two._id,
                    'type': 'registrations',
                    'attributes': {}
                }
            ]
        }

    @pytest.fixture()
    def bad_payload(self, registration_one, registration_two):
        return {
            'data': [
                {
                    'id': registration_one._id,
                    'type': 'registrations',
                    'attributes': {
                        'public': True,
                    }
                },
                {
                    'id': registration_two._id,
                    'type': 'registrations',
                    'attributes': {
                        'title': 'Nerds II: Attack of the Nerds',
                    }
                }
            ]
        }

    def test_bulk_update_errors(
            self, app, user, registration_one, registration_two,
            public_payload, private_payload, url):

        # test_bulk_update_registrations_blank_request
        res = app.put_json_api(
            url,
            auth=user.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 400

        # test_bulk_update_registrations_one_not_found
        payload = {'data': [
            {
                'id': '12345',
                'type': 'registrations',
                'attributes': {
                    'public': True,
                }
            }, public_payload['data'][0]
        ]}

        res = app.put_json_api(
            url, payload,
            auth=user.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

        # test_bulk_update_registrations_logged_out
        res = app.put_json_api(
            url, public_payload,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        # test_bulk_update_registrations_logged_in_non_contrib
        non_contrib = AuthUserFactory()
        res = app.put_json_api(
            url, private_payload,
            auth=non_contrib.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # test_bulk_update_registrations_send_dictionary_not_list
        res = app.put_json_api(
            url, {
                'data': {
                    'id': registration_one._id,
                    'type': 'nodes',
                    'attributes': {'public': True}
                }
            },
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

        # test_bulk_update_id_not_supplied
        res = app.put_json_api(
            url, {
                'data': [
                    public_payload['data'][1], {
                        'type': 'registrations',
                        'attributes': {'public': True}}
                ]
            },
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/id'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

        # test_bulk_update_type_not_supplied
        res = app.put_json_api(
            url, {
                'data': [
                    public_payload['data'][1], {
                        'id': registration_one._id,
                        'attributes': {'public': True}
                    }
                ]
            }, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/type'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

        # test_bulk_update_incorrect_type
        res = app.put_json_api(
            url, {
                'data': [
                    public_payload['data'][1], {
                        'id': registration_one._id,
                        'type': 'Incorrect',
                        'attributes': {'public': True}
                    }
                ]
            }, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409

        # test_bulk_update_limits
        registration_update_list = {'data': [public_payload['data'][0]] * 101}
        res = app.put_json_api(
            url,
            registration_update_list,
            auth=user.auth,
            expect_errors=True,
            bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        # 400 from attempting to make a registration private
        res = app.put_json_api(
            url,
            private_payload,
            auth=user.auth,
            bulk=True,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registrations can only be turned from private to public.'

        # Confirm no changes have occured
        registration_one.refresh_from_db()
        registration_two.refresh_from_db()

        assert registration_one.embargo_termination_approval is None
        assert registration_two.embargo_termination_approval is None

        assert registration_one.is_public is False
        assert registration_two.is_public is False

        assert registration_one.title == 'Birds'
        assert registration_two.title == 'Birds II'

    def test_bulk_update_embargo_logged_in_read_only_contrib(
            self, app, user, registration_one, registration_two, public_payload, url):
        read_contrib = AuthUserFactory()
        registration_one.add_contributor(
            read_contrib, permissions=permissions.READ, save=True)
        registration_two.add_contributor(
            read_contrib, permissions=permissions.READ, save=True)

        res = app.put_json_api(
            url,
            public_payload,
            auth=read_contrib.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_bulk_update_embargo_logged_in_contrib(
            self, app, user, registration_one, registration_two,
            public_payload, url):
        assert registration_one.is_pending_embargo_termination is False
        assert registration_two.is_pending_embargo_termination is False

        res = app.put_json_api(url, public_payload, auth=user.auth, bulk=True)
        assert res.status_code == 200
        assert ({registration_one._id, registration_two._id} == {
                res.json['data'][0]['id'], res.json['data'][1]['id']})

        # Needs confirmation before it will become public
        assert res.json['data'][0]['attributes']['public'] is False
        assert res.json['data'][1]['attributes']['public'] is False
        assert res.json['data'][0]['attributes']['pending_embargo_termination_approval'] is True
        assert res.json['data'][1]['attributes']['pending_embargo_termination_approval'] is True

        registration_one.refresh_from_db()
        registration_two.refresh_from_db()

        # registrations should have pending terminations
        assert registration_one.is_pending_embargo_termination is True
        assert registration_two.is_pending_embargo_termination is True


class TestRegistrationListFiltering(
        RegistrationListFilteringMixin,
        ApiTestCase):

    url = '/{}registrations/?'.format(API_BASE)
