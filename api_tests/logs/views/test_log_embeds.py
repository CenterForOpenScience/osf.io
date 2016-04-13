from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    RegistrationFactory
)


class TestLogEmbeds(ApiTestCase):


    def setUp(self):
        super(TestLogEmbeds, self).setUp()

        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.registration = RegistrationFactory(project=self.project, creator=self.user, is_public=True)

        self.first_reg_log = list(self.registration.logs)[0]

    def test_embed_original_node(self):
        registration_log_url = '/{}logs/{}/?embed=original_node'.format(API_BASE, self.first_reg_log._id)

        res = self.app.get(registration_log_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['action'], 'project_created')
        embeds = res.json['data']['embeds']['original_node']
        assert_equal(embeds['data']['id'], self.project._id)

    def test_embed_node(self):
        registration_log_url = '/{}logs/{}/?embed=node'.format(API_BASE, self.first_reg_log._id)

        res = self.app.get(registration_log_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['action'], 'project_created')
        embeds = res.json['data']['embeds']['node']
        assert_equal(embeds['data']['id'], self.registration._id)

    def test_embed_user(self):
        registration_log_url = '/{}logs/{}/?embed=user'.format(API_BASE, self.first_reg_log._id)

        res = self.app.get(registration_log_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['action'], 'project_created')
        embeds = res.json['data']['embeds']['user']
        assert_equal(embeds['data']['id'], self.user._id)

    def test_embed_attributes_not_relationships(self):
        url = '/{}logs/{}/?embed=action'.format(API_BASE, self.first_reg_log._id)

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "The following fields are not embeddable: action")
