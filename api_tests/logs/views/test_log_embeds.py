import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    RegistrationFactory,
)


@pytest.mark.django_db
class TestLogEmbeds:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def registration(self, user, project):
        return RegistrationFactory(
            project=project, creator=user, is_public=True)

    @pytest.fixture()
    def registration_log(self, registration):
        return registration.logs.order_by('date').first()

    @pytest.fixture()
    def make_url_registration_log(self, registration_log):
        def url_registration_log(type_embed):
            return '/{}logs/{}/?embed={}'.format(
                API_BASE, registration_log._id, type_embed)
        return url_registration_log

    def test_log_embed_types(
            self, app, make_url_registration_log,
            user, project, registration):

        # test_embed_original_node
        url_registration_log = make_url_registration_log(
            type_embed='original_node')

        res = app.get(url_registration_log, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['action'] == 'project_created'
        embeds = res.json['data']['embeds']['original_node']
        assert embeds['data']['id'] == project._id

        # test_embed_node
        url_registration_log = make_url_registration_log(type_embed='node')

        res = app.get(url_registration_log, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['action'] == 'project_created'
        embeds = res.json['data']['embeds']['node']
        assert embeds['data']['id'] == registration._id

        # test_embed_user
        url_registration_log = make_url_registration_log(type_embed='user')

        res = app.get(url_registration_log, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['action'] == 'project_created'
        embeds = res.json['data']['embeds']['user']
        assert embeds['data']['id'] == user._id

        # test_embed_attributes_not_relationships
        url_registration_log = make_url_registration_log(type_embed='action')

        res = app.get(url_registration_log, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The following fields are not embeddable: action'
