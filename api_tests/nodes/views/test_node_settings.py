# -*- coding: utf-8 -*-
import pytest
from framework.auth import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    PrivateLinkFactory,
)
from osf.models import NodeLog

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
    project.add_contributor(write_contrib, ['write', 'read'])
    project.add_contributor(read_contrib, ['read'])
    project.save()
    return project

@pytest.fixture()
def url(project):
    return '/{}nodes/{}/settings/'.format(API_BASE, project._id)


@pytest.mark.django_db
class TestNodeSettingsGet:

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
        assert attributes['access_requests_enabled'] is True

        # anyone can comment
        project.comment_level = 'public'
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['anyone_can_comment'] is True

        project.comment_level = 'private'
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['anyone_can_comment'] is False

        # wiki enabled
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['wiki_enabled'] is True

        project.delete_addon('wiki', auth=Auth(admin_contrib))
        project.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['wiki_enabled'] is False

        # redirect link enabled
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['redirect_link_enabled'] is False
        assert attributes['redirect_link_url'] is None
        assert attributes['redirect_link_label'] is None

        new_url = 'http://cool.com'
        new_label = 'Test Label Woo'
        forward = project.add_addon('forward', auth=Auth(admin_contrib))
        forward.url = new_url
        forward.label = new_label
        forward.save()
        res = app.get(url, auth=admin_contrib.auth)
        attributes = res.json['data']['attributes']
        assert attributes['redirect_link_enabled'] is True
        assert attributes['redirect_link_url'] == new_url
        assert attributes['redirect_link_label'] == new_label

        # view only links
        view_only_link = PrivateLinkFactory(name='testlink')
        view_only_link.nodes.add(project)
        view_only_link.save()
        res = app.get(url, auth=admin_contrib.auth)
        assert 'view_only_links' in res.json['data']['relationships'].keys()


@pytest.mark.django_db
class TestNodeSettingsPUT:
    @pytest.fixture()
    def payload(self, project):
        return {
            'data': {
                'id': project._id,
                'type': 'node-settings',
                'attributes': {
                    'redirect_link_enabled': True,
                    'redirect_link_url': 'https://cos.io'
                }
            }
        }

    def test_put_permissions(self, app, project, payload, admin_contrib, write_contrib, read_contrib, url):
        assert project.access_requests_enabled is True
        payload['data']['attributes']['access_requests_enabled'] = False
        # Logged out
        res = app.put_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, noncontrib
        noncontrib = AuthUserFactory()
        res = app.put_json_api(url, payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in read
        res = app.put_json_api(url, payload, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in write (Write contribs can only change some node settings)
        res = app.put_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in admin
        res = app.put_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200


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
        assert res.status_code == 200

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200

    def test_patch_invalid_type(self, app, project, payload, admin_contrib, url):
        payload['data']['type'] = 'Invalid Type'

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 409

    def test_patch_access_requests_enabled(self, app, project, payload, admin_contrib, write_contrib, url):
        assert project.access_requests_enabled is True
        payload['data']['attributes']['access_requests_enabled'] = False

        # Write cannot modify this field
        res = app.patch_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        project.reload()
        assert project.access_requests_enabled is False
        assert project.logs.latest().action == NodeLog.NODE_ACCESS_REQUESTS_DISABLED
        assert res.json['data']['attributes']['access_requests_enabled'] is False

        payload['data']['attributes']['access_requests_enabled'] = True
        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        project.reload()
        assert project.access_requests_enabled is True
        assert project.logs.latest().action == NodeLog.NODE_ACCESS_REQUESTS_ENABLED
        assert res.json['data']['attributes']['access_requests_enabled'] is True

    def test_patch_anyone_can_comment(self, app, project, payload, admin_contrib, write_contrib, url):
        assert project.comment_level == 'public'
        payload['data']['attributes']['anyone_can_comment'] = False

        # Write cannot modify this field
        res = app.patch_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        project.reload()
        assert project.comment_level == 'private'
        assert res.json['data']['attributes']['anyone_can_comment'] is False

        payload['data']['attributes']['anyone_can_comment'] = True
        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        project.reload()
        assert project.comment_level == 'public'
        assert res.json['data']['attributes']['anyone_can_comment'] is False

    def test_patch_anyone_can_edit_wiki(self, app, project, payload, admin_contrib, write_contrib, url):
        project.is_public = True
        project.save()
        wiki_addon = project.get_addon('wiki')
        assert wiki_addon.is_publicly_editable is False
        payload['data']['attributes']['anyone_can_edit_wiki'] = False

        # Write cannot modify this field
        res = app.patch_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        wiki_addon.reload()
        assert wiki_addon.is_publicly_editable is True
        assert project.logs.latest().action == NodeLog.MADE_WIKI_PUBLIC
        assert res.json['data']['attributes']['anyone_can_edit_wiki'] is True

        payload['data']['attributes']['anyone_can_edit_wiki'] = False
        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        wiki_addon.reload()
        assert wiki_addon.is_publicly_editable is False
        assert project.logs.latest().action == NodeLog.MADE_WIKI_PRIVATE
        assert res.json['data']['attributes']['anyone_can_edit_wiki'] is False

        # Test wiki disabled in same request so cannot change wiki_settings
        payload['data']['attributes']['wiki_enabled'] = False
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400

        # Test wiki disabled so cannot change wiki settings
        project.delete_addon('wiki', Auth(admin_contrib))
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400

        # Test wiki enabled so can change wiki settings
        payload['data']['attributes']['wiki_enabled'] = True
        payload['data']['attributes']['anyone_can_edit_wiki'] = True
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        assert project.get_addon('wiki').is_publicly_editable is True
        assert project.logs.latest().action == NodeLog.MADE_WIKI_PUBLIC
        assert res.json['data']['attributes']['anyone_can_edit_wiki'] is True

        # If project is private, cannot change settings to allow anyone to edit wiki
        project.is_public = False
        project.save()
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'To allow all OSF users to edit the wiki, the project must be public.'

    def test_patch_wiki_enabled(self, app, project, payload, admin_contrib, write_contrib, url):
        assert project.get_addon('wiki') is not None
        payload['data']['attributes']['wiki_enabled'] = False

        # Write cannot modify this field
        res = app.patch_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        assert project.get_addon('wiki') is None
        assert res.json['data']['attributes']['wiki_enabled'] is False

        # Nothing happens if attempting to disable an already-disabled wiki
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        assert project.get_addon('wiki') is None

        payload['data']['attributes']['wiki_enabled'] = True
        # Logged in admin
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        assert project.get_addon('wiki') is not None
        assert res.json['data']['attributes']['wiki_enabled'] is True

        # Nothing happens if attempting to enable an already-enabled-wiki
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        assert project.get_addon('wiki') is not None

    def test_redirect_link_enabled(self, app, project, payload, admin_contrib, write_contrib, url):
        assert project.get_addon('forward') is None
        payload['data']['attributes']['redirect_link_enabled'] = True

        label = 'My Link'
        url = 'https://cos.io'

        # Redirect link not included
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You must include a redirect URL to enable a redirect.'

        payload['data']['attributes']['redirect_link_url'] = url
        payload['data']['attributes']['redirect_link_label'] = label
        # Write contrib can modify forward related fields
        res = app.patch_json_api(url, payload, auth=write_contrib.auth)
        assert res.status_code == 200
        forward_addon = project.get_addon('forward')
        assert forward_addon is not None
        assert forward_addon.url == url
        assert forward_addon.label == 'My Link'
        assert project.logs.latest().action == 'forward_url_changed'
        assert res.json['data']['attributes']['redirect_link_enabled'] is True
        assert res.json['data']['attributes']['redirect_link_url'] == url
        assert res.json['data']['attributes']['redirect_link_label'] == label

        # Attempting to set redirect_link_url when redirect_link not enabled
        payload['data']['attributes']['redirect_link_enabled'] = False
        del payload['data']['attributes']['redirect_link_label']
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You must first set redirect_link_enabled to True before specifying a redirect link URL.'

        # Attempting to set redirect_link_label when redirect_link not enabled
        payload['data']['attributes']['redirect_link_enabled'] = False
        del payload['data']['attributes']['redirect_link_url']
        payload['data']['attributes']['redirect_link_label'] = 'My Link'
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You must first set redirect_link_enabled to True before specifying a redirect link label.'

        payload['data']['attributes']['redirect_link_enabled'] = False
        del payload['data']['attributes']['redirect_link_label']
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth)
        assert res.status_code == 200
        forward_addon = project.get_addon('forward')
        assert forward_addon is None
        assert res.json['data']['attributes']['redirect_link_enabled'] is False
        assert res.json['data']['attributes']['redirect_link_url'] is None
        assert res.json['data']['attributes']['redirect_link_label'] is None

    def test_redirect_link_label_char_limit(self, app, project, payload, admin_contrib, url):
        project.add_addon('forward', ())
        project.save()

        payload['data']['attributes']['redirect_link_label'] = 'a' * 52
        res = app.patch_json_api(url, payload, auth=admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Ensure this field has no more than 50 characters.'
