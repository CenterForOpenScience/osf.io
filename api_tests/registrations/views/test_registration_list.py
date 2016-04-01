
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from website.models import Node
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE


from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CollectionFactory,
    BookmarkCollectionFactory
)


class TestRegistrationList(ApiTestCase):

    def setUp(self):
        super(TestRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)
        self.url = '/{}registrations/'.format(API_BASE)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project, is_public=True)
        self.user_two = AuthUserFactory()

    def tearDown(self):
        super(TestRegistrationList, self).tearDown()
        Node.remove()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = res.json['data'][0]['relationships']['registered_from']['links']['related']['href']
        assert_equal(urlparse(url).path, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_return_registrations_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.status_code, 200)

        registered_from_one = urlparse(res.json['data'][0]['relationships']['registered_from']['links']['related']['href']).path
        registered_from_two = urlparse(res.json['data'][1]['relationships']['registered_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_items_equal([registered_from_one, registered_from_two],
                           ['/{}nodes/{}/'.format(API_BASE, self.public_project._id),
                            '/{}nodes/{}/'.format(API_BASE, self.project._id)])

    def test_return_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        registered_from = urlparse(res.json['data'][0]['relationships']['registered_from']['links']['related']['href']).path

        assert_equal(res.content_type, 'application/vnd.api+json')

        assert_equal(registered_from, '/{}nodes/{}/'.format(API_BASE, self.public_project._id))

    def test_exclude_nodes_from_registrations_endpoint(self):
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.registration_project._id, ids)
        assert_in(self.public_registration_project._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.project._id, ids)


class TestRegistrationFiltering(ApiTestCase):

    def setUp(self):
        super(TestRegistrationFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", description='Two', is_public=True, creator=self.user_one, category='hypothesis')
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True, creator=self.user_one)
        self.project_three = ProjectFactory(title="Three", is_public=True, creator=self.user_two)


        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)

        self.project_one.add_tag('tag1', Auth(self.project_one.creator), save=False)
        self.project_one.add_tag('tag2', Auth(self.project_one.creator), save=False)
        self.project_one.save()
        self.project_two.add_tag('tag1', Auth(self.project_two.creator), save=True)
        self.project_two.save()

        self.project_one_reg = RegistrationFactory(creator=self.user_one, project=self.project_one, is_public=True)
        self.project_two_reg = RegistrationFactory(creator=self.user_one, project=self.project_two, is_public=True)
        self.project_three_reg = RegistrationFactory(creator=self.user_two, project=self.project_three, is_public=True)
        self.private_project_user_one_reg = RegistrationFactory(creator=self.user_one, project=self.private_project_user_one, is_public=False)
        self.private_project_user_two_reg = RegistrationFactory(creator=self.user_two, project=self.private_project_user_two, is_public=False)

        self.folder = CollectionFactory()
        self.bookmark_collection = BookmarkCollectionFactory()

        self.url = "/{}registrations/".format(API_BASE)

    def tearDown(self):
        super(TestRegistrationFiltering, self).tearDown()
        Node.remove()

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
        url = '/{}registrations/?filter[tags]={}&filter[tags]={}'.format(API_BASE, 'tag1', 'tag2')

        res = self.app.get(url, auth=self.project_one.creator.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.project_one_reg._id, ids)
        assert_not_in(self.project_two_reg._id, ids)
        assert_not_in(self.project_three_reg._id, ids)
        assert_not_in(self.private_project_user_one_reg._id, ids)
        assert_not_in(self.private_project_user_two_reg._id, ids)

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
        url = "/{}registrations/?filter[title]=Project%20One".format(API_BASE)

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
        url = "/{}registrations/?filter[title]=Private%20Project%20User%20One".format(API_BASE)

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
        url = "/{}registrations/?filter[title]=Two".format(API_BASE)

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
        url = "/{}registrations/?filter[title]=One".format(API_BASE)

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
        url = "/{}registrations/?filter[title]=Project".format(API_BASE)

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
        url = "/{}registrations/?filter[title]=Project".format(API_BASE)

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
        url = "/{}registrations/?filter[description]=Three".format(API_BASE)

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
        url = "/{}registrations/?filter[description]=Two".format(API_BASE)

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
        assert_equal(errors[0]['detail'], "'notafield' is not a valid field for this endpoint.")
