
# -*- coding: utf-8 -*-
import mock
import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
)


@pytest.mark.django_db
class TestNodeSettingsUpdate:

    @pytest.fixture()
    def admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, admin_contrib, write_contrib, read_contrib):
        project = ProjectFactory(creator=admin_contrib)
        project.add_contributor(write_contrib, 'write')
        project.add_contributor(read_contrib, 'write')
        project.save()
        return project

    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/settings/'.format(API_BASE, project._id)

    @pytest.fixture()
    def payload(self, project):
        return {
            'data': {
                'id': project._id,
                'type': 'node-settings',
                'attributes': {
                }
            }
        }


    def test_patch_permissions(self, app, project, payload, admin_contrib, write_contrib, read_contrib, url):
        payload['data']['attributes']['redirect_link_enabled'] = True
        payload['data']['attributes']['redirect_link_url'] = 'https://cos.io'
        # Logged out
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, noncontrib
        noncontrib = AuthUserFactory()
        res = app.patch_json_api(url, payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in read
        res = app.patch_json_api(url, payload, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in write (Write contribs can only change some node settings)
        res = app.patch_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
