from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth, Q
from api.base.settings.defaults import API_BASE
from website.models import Node

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory
)


class TestPreprintList(ApiTestCase):

    def setUp(self):
        super(TestPreprintList, self).setUp()
        self.user = AuthUserFactory()

        self.preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/'.format(API_BASE)

        self.project = ProjectFactory(creator=self.user)

    def tearDown(self):
        super(TestPreprintList, self).tearDown()
        Node.remove()

    def test_return_preprints_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_exclude_nodes_from_preprints_endpoint(self):
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.project._id, ids)



class TestPreprintFiltering(ApiTestCase):

    def setUp(self):
        super(TestPreprintFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user, provider='wwe')
        self.url = "/{}registrations/".format(API_BASE)

        self.preprint.add_tag('nature boy', Auth(self.user), save=False)
        self.preprint.add_tag('ric flair', Auth(self.user), save=False)
        self.preprint.save()

        self.preprint_two = PreprintFactory(creator=self.user, filename='woo.txt', provider='wcw')
        self.preprint_two.add_tag('nature boy', Auth(self.user), save=False)
        self.preprint_two.add_tag('woo', Auth(self.user), save=False)
        self.preprint_two.save()

        self.preprint_three = PreprintFactory(creator=self.user, filename='stonecold.txt', provider='wwe')
        self.preprint_three.add_tag('stone', Auth(self.user), save=False)
        self.preprint_two.add_tag('cold', Auth(self.user), save=False)
        self.preprint_three.save()

    def tearDown(self):
        super(TestPreprintFiltering, self).tearDown()
        Node.remove()

    def test_filtering_tags(self):
        # both preprint and preprint_two have nature boy
        url = '/{}preprints/?filter[tags]={}'.format(API_BASE, 'nature boy')

        res = self.app.get(url, auth=self.user.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.preprint._id, ids)
        assert_in(self.preprint_two._id, ids)
        assert_not_in(self.preprint_three._id, ids)

        # filtering two tags
        # preprint has both tags; preprint_two only has one
        url = '/{}preprints/?filter[tags]={}&filter[tags]={}'.format(API_BASE, 'nature boy', 'ric flair')

        res = self.app.get(url, auth=self.user.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.preprint_two._id, ids)
        assert_not_in(self.preprint_three._id, ids)

    def test_filter_by_provider(self):
        url = '/{}preprints/?filter[provider]={}'.format(API_BASE, 'wwe')
        res = self.app.get(url, auth=self.user.auth)
        data = res.json['data']

        assert_equal(len(data), 2)
        for result in data:
            assert 'wwe' in result['attributes']['provider']
