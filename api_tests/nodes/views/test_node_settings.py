# -*- coding: utf-8 -*-
import mock
import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    PrivateLinkFactory,
)

from framework.auth import Auth


@pytest.fixture()
def admin_contrib():
    return AuthUserFactory()

@pytest.fixture()
def write_contrib():
    return AuthUserFactory()

@pytest.fixture()
def read_contrib():
    return AuthUserFactory()

@pytest.fixture()
def project(admin_contrib, write_contrib, read_contrib):
    project = ProjectFactory(creator=admin_contrib)
    project.add_contributor(write_contrib, 'write')
    project.add_contributor(read_contrib, 'write')
    project.save()
    return project

@pytest.fixture()
def url(project):
    return '/{}nodes/{}/settings/'.format(API_BASE, project._id)


@pytest.mark.django_db
class TestGetNodeSettingsGet:

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    def test_node_settings_detail(self, app, admin_contrib, non_contrib, write_contrib, url, project):

        # non logged in uers can't access node settings
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # non_contrib can't access node settings
        res = app.get(url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # read contrib can access node settings
        res = app.get(url, auth=write_contrib.auth)
        assert res.status_code == 200

        # admin can access node settings
        res = app.get(url, auth=admin_contrib.auth)
        assert res.status_code == 200

        # allow_access_requests
        project.allow_access_requests = True
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['access_requests_enabled'] == True

        # anyone can comment
        project.comment_level = 'public'
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['anyone_can_comment'] == True

        project.comment_level = 'private'
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['anyone_can_comment'] == False

        # wiki enabled
        project.delete_addon('wiki', auth=Auth(admin_contrib))
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['wiki_enabled'] == False

        # redirect link enabled
        new_url = 'http://cool.com'
        new_label = 'Test Label Woo'
        forward = project.add_addon('forward', auth=Auth(admin_contrib))
        forward.url = new_url
        forward.label = new_label
        forward.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['redirect_link_enabled'] == True
        assert attributes['redirect_link_url'] == new_url
        assert attributes['redirect_link_label'] == new_label

        # view only links
        view_only_link = PrivateLinkFactory(name='testlink')
        view_only_link.nodes.add(project)
        view_only_link.save()
        res = app.get(url, auth=admin_contrib.auth)
        assert 'view_only_links' in res.json['data']['relationships'].keys()

@pytest.mark.django_db
class TestNodeSettingsUpdate:

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
