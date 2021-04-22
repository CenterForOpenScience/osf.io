# -*- coding: utf-8 -*-

import sys
import json
import requests
import string
import random
import base64
from urllib.parse import urlencode
from urllib.parse import urlparse

from django.utils import timezone

import mock
import pytest
from nose.tools import *  # noqa PEP8 asserts

from framework.auth.core import Auth
from osf.models import AbstractNode, NodeLog
from osf.models.mapcore import MAPProfile
from osf.utils.permissions import (CREATOR_PERMISSIONS,
                                   DEFAULT_CONTRIBUTOR_PERMISSIONS)
from api.base.settings.defaults import API_BASE
from scripts.populate_institutions import SHIBBOLETH_SP_LOGIN
from tests.base import fake, OsfTestCase
from website import settings
from website.util import web_url_for
from website.profile.utils import add_contributor_json
from nii.mapcore import (encode_uri_component,
                         mapcore_disable_log,
                         mapcore_sync_is_enabled,
                         mapcore_sync_set_enabled,
                         mapcore_sync_set_disabled,
                         mapcore_sync_upload_all,
                         mapcore_api_is_available,
                         mapcore_request_authcode,
                         mapcore_receive_authcode)
from nii.mapcore_api import (MAPCore, MAPCoreTokenExpired, OPEN_MEMBER_PUBLIC)

from tests.utils import assert_latest_log
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import (fake_email,
                                 AuthUserFactory,
                                 UserFactory,
                                 ProjectFactory,
                                 BookmarkCollectionFactory,
                                 InstitutionFactory)

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        sys.stderr.write('DEBUG: {}\n'.format(msg))

def randstr(n):
    r = [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    return ''.join(r)


@pytest.mark.django_db
class TestOAuthOfMAPCore(OsfTestCase):
    def setUp(self):
        mapcore_disable_log()
        OsfTestCase.setUp(self)
        self.me = AuthUserFactory()
        self.me.eppn = fake_email()
        self.inst = InstitutionFactory()
        self.entity_id = encode_uri_component(self.inst.login_url)
        self.inst.login_url = SHIBBOLETH_SP_LOGIN.format(self.entity_id)
        self.inst.logout_url = None
        self.inst.save()
        self.me.affiliated_institutions.add(self.inst)
        self.me.save()

    def test_no_map_profile(self):
        assert_equal(self.me.map_profile, None)
        with assert_raises(MAPCoreTokenExpired):
            mapcore_api_is_available(self.me)

    def _common_mapcore_request_authcode_with_next_url(self, next_url):
        client_id = 'fake_clientid'
        entity_id = self.entity_id
        if next_url is not None:
            state_str = base64.b64encode((settings.MAPCORE_AUTHCODE_MAGIC + next_url).encode('utf-8')).decode()
        else:
            state_str = settings.MAPCORE_AUTHCODE_MAGIC
        redirect_uri = settings.DOMAIN + web_url_for('mapcore_oauth_complete')[1:]
        next_params = {'response_type': 'code',
                    'redirect_uri': redirect_uri,
                    'client_id': client_id,
                    'state': state_str}
        url = settings.MAPCORE_HOSTNAME + settings.MAPCORE_AUTHCODE_PATH
        target = url + '?' + urlencode(next_params)

        params = {'next_url': next_url}
        redirect_url = mapcore_request_authcode(self.me, params)
        if entity_id:
            expected_url = '{}/Shibboleth.sso/DS?entityID={}&target={}'.format(
                settings.MAPCORE_HOSTNAME,
                entity_id, encode_uri_component(target))
        else:
            expected_url = target
        assert_equal(redirect_url, expected_url)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'fake_clientid')
    def test_mapcore_request_authcode_with_next_url(self):
        next_url = web_url_for('dashboard')
        self._common_mapcore_request_authcode_with_next_url(next_url)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'fake_clientid')
    def test_mapcore_request_authcode_without_next_url(self):
        next_url = None
        self._common_mapcore_request_authcode_with_next_url(next_url)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'fake_clientid')
    def test_mapcore_request_authcode_without_entity_id(self):
        self.entity_id = None
        self.inst.login_url = None
        self.inst.save()
        next_url = None
        self._common_mapcore_request_authcode_with_next_url(next_url)

    # test mapcore_receive_authcode()
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_refresh_token')
    @mock.patch('nii.mapcore.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore.mapcore_get_accesstoken')
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_refresh_token(self, mock_post, mock_req, mock_token):
        ACCESS_TOKEN = 'ABCDE'
        REFRESH_TOKEN = '12345'
        mock_token.return_value = (ACCESS_TOKEN, REFRESH_TOKEN)
        next_url = u'http://nexturl.example.com/\u00c3\u00c3\u00c3'
        state = settings.MAPCORE_AUTHCODE_MAGIC + next_url
        params = {'code': 'abc', 'state': base64.b64encode(state.encode('utf-8')).decode()}
        assert_equal(self.me.map_profile, None)
        # set self.me.map_profile
        ret = mapcore_receive_authcode(self.me, params)
        assert_equal(next_url, ret)

        self.me.reload()
        assert_equal(self.me.map_profile.oauth_access_token, ACCESS_TOKEN)
        assert_equal(self.me.map_profile.oauth_refresh_token, REFRESH_TOKEN)

        api_version = requests.Response()
        api_version.status_code = requests.codes.ok
        api_version._content = '{ "result": { "version": 2, "revision": 1, "author": "abcde" }, "status": { "error_code": 0 } }'
        mock_req.return_value = api_version

        ACCESS_TOKEN2 = ACCESS_TOKEN + '_2'
        REFRESH_TOKEN2 = REFRESH_TOKEN + '_2'
        refresh_token = requests.Response()
        refresh_token.status_code = requests.codes.ok
        refresh_token._content = '{ "access_token": "' + ACCESS_TOKEN2 + '", "refresh_token": "' + REFRESH_TOKEN2 + '" }'
        mock_post.return_value = refresh_token

        mapcore_api_is_available(self.me)
        self.me.reload()
        # tokens are not updated (refresh_token() is not called)
        assert_equal(self.me.map_profile.oauth_access_token, ACCESS_TOKEN)
        assert_equal(self.me.map_profile.oauth_refresh_token, REFRESH_TOKEN)

        api_version_e = requests.Response()
        api_version_e.status_code = 401
        api_version_e.headers = {'WWW-Authenticate': '[TEST] auth error'}
        api_version_e._content = '{}'
        mock_req.side_effect = [api_version_e, api_version]  # two times

        mapcore_api_is_available(self.me)
        self.me.reload()
        # tokens are updated (refresh_token() is called)
        assert_equal(self.me.map_profile.oauth_access_token, ACCESS_TOKEN2)
        assert_equal(self.me.map_profile.oauth_refresh_token, REFRESH_TOKEN2)



def fake_map_profile():
    p = MAPProfile.objects.create()
    p.oauth_access_token = 'fake_access_token'
    p.oauth_refresh_token = 'fake_refresh_token'
    p.oauth_refresh_time = timezone.now()
    p.save()
    return p


@pytest.mark.django_db
class TestFuncOfMAPCore(OsfTestCase):

    def setUp(self):
        mapcore_disable_log()
        OsfTestCase.setUp(self)

        self.me = AuthUserFactory()
        self.me.eppn = 'ME+' + fake_email()
        self.me.map_profile = fake_map_profile()
        self.me.save()
        BookmarkCollectionFactory(creator=self.me)

        self.user2 = AuthUserFactory()
        self.user2.eppn = 'USER2+' + fake_email()
        self.user2.map_profile = fake_map_profile()
        self.user2.save()

        self.project = ProjectFactory(
            creator=self.me,
            is_public=True,
            title=fake.bs(),
            map_group_key=None,
        )
        self.project_url = self.project.web_url_for('view_project')
        self.project.save()

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', None)
    def test_sync_is_disabled(self):
        assert_equal(mapcore_sync_is_enabled(), False)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_enabled')
    def test_sync_is_enabled(self):
        assert_equal(mapcore_sync_is_enabled(), True)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'dummy_client_id')
    def test_sync_set_enabled(self):
        mapcore_sync_set_disabled()
        assert_equal(mapcore_sync_is_enabled(), False)
        mapcore_sync_set_enabled()
        assert_equal(mapcore_sync_is_enabled(), True)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'dummy_client_id')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group')
    def test_sync_upload_all(self, mock_sync):
        mapcore_sync_set_disabled()
        mapcore_sync_upload_all()
        assert_equal(mock_sync.call_count, 0)
        mapcore_sync_set_enabled()
        mapcore_sync_upload_all()
        assert_not_equal(mock_sync.call_count, 0)
        # testing mapcore_set_standby_to_upload() exists in test_sync_rdm_project_or_map_group

    # include testing mapcore_set_standby_to_upload()
    def test_sync_rdm_project_or_map_group(self):
        from nii.mapcore import (mapcore_sync_rdm_project_or_map_group,
                                 mapcore_is_sync_time_expired,
                                 mapcore_clear_sync_time,
                                 mapcore_set_standby_to_upload,
                                 mapcore_unset_standby_to_upload)

        # create a new group (GRDM -> mAP)
        assert_equal(self.project.map_group_key, None)
        with mock.patch('nii.mapcore.mapcore_sync_map_new_group') as mock1, \
             mock.patch('nii.mapcore.mapcore_sync_map_group') as mock2, \
             mock.patch('nii.mapcore.mapcore_sync_rdm_project') as mock3:
            mock1.return_value = 'fake_group_key'
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock1.call_count, 1)
            assert_equal(mock2.call_count, 1)
            assert_equal(mock3.call_count, 0)

        # GRDM -> mAP
        # use mock: mapcore_is_on_standby_to_upload
        mapcore_clear_sync_time(self.project)
        self.project.map_group_key = 'fake_group_key'
        self.project.save()
        with mock.patch('nii.mapcore.mapcore_is_on_standby_to_upload') as mock1, \
             mock.patch('nii.mapcore.mapcore_sync_map_group') as mock2:
            mock1.return_value = True
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock1.call_count, 1)
            assert_equal(mock2.call_count, 1)

        # GRDM -> mAP
        # not use mock: mapcore_is_on_standby_to_upload
        mapcore_clear_sync_time(self.project)
        with mock.patch('nii.mapcore.mapcore_sync_map_group') as mock1:
            mapcore_set_standby_to_upload(self.project, log=True)
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock1.call_count, 1)

        # mAP -> GRDM
        # use mock: mapcore_is_on_standby_to_upload
        mapcore_clear_sync_time(self.project)
        with mock.patch('nii.mapcore.mapcore_is_on_standby_to_upload') as mock1, \
             mock.patch('nii.mapcore.mapcore_sync_rdm_project') as mock2:
            assert_equal(mapcore_is_sync_time_expired(self.project), True)
            mock1.return_value = False
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock1.call_count, 1)
            assert_equal(mock2.call_count, 1)
            self.project.reload()
            assert_equal(mapcore_is_sync_time_expired(self.project), False)
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock1.call_count, 1)  # not incremented
            assert_equal(mock2.call_count, 1)  # not incremented

        # mAP -> GRDM
        # not use mock: mapcore_is_on_standby_to_upload
        mapcore_clear_sync_time(self.project)
        with mock.patch('nii.mapcore.mapcore_sync_rdm_project') as mock2:
            assert_equal(mapcore_is_sync_time_expired(self.project), True)
            mapcore_unset_standby_to_upload(self.project)
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock2.call_count, 1)
            self.project.reload()
            assert_equal(mapcore_is_sync_time_expired(self.project), False)
            mapcore_sync_rdm_project_or_map_group(self.me, self.project)
            assert_equal(mock2.call_count, 1)  # not incremented


    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('requests.post')
    @mock.patch('nii.mapcore_api.MAPCore.edit_group')
    def test_sync_map_new_group(self, mock_edit, mock_post):
        from nii.mapcore import mapcore_sync_map_new_group

        create_group = requests.Response()
        create_group.status_code = requests.codes.ok
        create_group._content = '{"result": {"groups": [{"group_key": "fake_group_key"}]}, "status": {"error_code": 0} }'
        mock_post.return_value = create_group
        mock_edit.return_value = json.loads(create_group.content)

        mapcore_sync_map_new_group(self.me, self.project, use_raise=True)
        args, kwargs = mock_post.call_args
        assert_equal(args[0].endswith('/group'), True)
        assert_equal(mock_edit.call_count, 1)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('requests.post')
    def test_sync_map_group_title_desc(self, mock_post):
        from nii.mapcore import mapcore_sync_map_group

        edit_group = requests.Response()
        edit_group.status_code = requests.codes.ok
        edit_group._content = '{"result": {"groups": [{"group_key": "fake_group_key"}]}, "status": {"error_code": 0} }'
        mock_post.return_value = edit_group

        self.project.map_group_key = 'fake_group_key'
        self.project.save()
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=True, contributors=False,
                               use_raise=True)
        args, kwargs = mock_post.call_args
        assert_equal(args[0].endswith('/group/' + self.project.map_group_key),
                     True)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_extended_group_info')
    @mock.patch('nii.mapcore.mapcore_add_to_group')
    @mock.patch('nii.mapcore.mapcore_remove_from_group')
    @mock.patch('nii.mapcore.mapcore_edit_member')
    def test_sync_map_group_contributors(self, mock_edit, mock_remove, mock_add, mock_get_grinfo):
        from nii.mapcore import mapcore_sync_map_group

        # test #1 : same member list
        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER}]}
        self.project.map_group_key = 'fake_group_key'
        self.project.add_contributor(self.user2, DEFAULT_CONTRIBUTOR_PERMISSIONS, save=False)
        self.project.save()
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 0)
        mock_get_grinfo.call_count = 0

        # test #2 : add
        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN}]}
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 1)
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 0)
        mock_get_grinfo.call_count = 0
        mock_add.call_count = 0
        self.project.remove_contributor(self.user2, auth=Auth(self.me))
        self.project.save()

        # test #3 : remove
        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER}]}
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 1)
        assert_equal(mock_edit.call_count, 0)
        mock_get_grinfo.call_count = 0
        mock_remove.call_count = 0

        # test #4 : set MODE_ADMIN
        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER}]}
        self.project.add_contributor(self.user2, CREATOR_PERMISSIONS, save=False)
        self.project.save()
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 1)
        args, kwargs = mock_edit.call_args
        assert_equal(args[3], self.user2.eppn)
        assert_equal(args[4], MAPCore.MODE_ADMIN)
        mock_get_grinfo.call_count = 0
        mock_edit.call_count = 0

        # test #5 : set MODE_MEMBER
        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_ADMIN}]}
        self.project.set_permissions(self.user2, DEFAULT_CONTRIBUTOR_PERMISSIONS, save=False)
        self.project.save()
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 1)
        args, kwargs = mock_edit.call_args
        assert_equal(args[3], self.user2.eppn)
        assert_equal(args[4], MAPCore.MODE_MEMBER)

        self.project.remove_contributor(self.user2, auth=Auth(self.me))
        self.project.save()

    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_sync_map_group_error(self, mock_sync):
        from nii.mapcore import mapcore_sync_map_group

        mock_sync.side_effect = Exception('fake error message')
        mapcore_sync_map_group(self.me, self.project, use_raise=False)
        assert_equal(mock_sync.call_count, 1)
        node_copy = AbstractNode.objects.get(guids___id=self.project._id)
        assert_equal(node_copy.logs.latest().action,
                     NodeLog.MAPCORE_MAP_GROUP_NOT_UPDATED)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_extended_group_info')
    @mock.patch('nii.mapcore.mapcore_add_to_group')
    @mock.patch('nii.mapcore.mapcore_remove_from_group')
    @mock.patch('nii.mapcore.mapcore_edit_member')
    def test_sync_map_ignore_unregistered_osfuser(self, mock_edit, mock_remove, mock_add, mock_get_grinfo):
        from nii.mapcore import mapcore_sync_map_group

        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': 'UNKNOWN_USER+' + self.user2.eppn, 'admin': MAPCore.MODE_MEMBER}]}
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 0)  # not called
        assert_equal(mock_edit.call_count, 0)
        node_copy = AbstractNode.objects.get(guids___id=self.project._id)
        assert_equal(node_copy.logs.latest().action,
                     NodeLog.MAPCORE_RDM_UNKNOWN_USER)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_group_by_key')
    @mock.patch('nii.mapcore.mapcore_get_group_members')
    @mock.patch('nii.mapcore.mapcore_add_to_group')
    @mock.patch('nii.mapcore.mapcore_remove_from_group')
    @mock.patch('nii.mapcore.mapcore_edit_member')
    def test_sync_map_ignore_unconfirmed_invited_member(self, mock_edit, mock_remove, mock_add, mock_get_members, mock_get_group):
        from nii.mapcore import mapcore_sync_map_group

        mock_get_group.return_value = {
            'result': {'groups': [{
                'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
                'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC}]}}
        mock_get_members.return_value = {
            'result': {'accounts': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': None, 'admin': MAPCore.MODE_MEMBER},
                {'admin': MAPCore.MODE_MEMBER},
                {}]}}
        mapcore_sync_map_group(self.me, self.project,
                               title_desc=False, contributors=True,
                               use_raise=True)
        assert_equal(mock_get_group.call_count, 1)
        assert_equal(mock_get_members.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 0)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('requests.get')
    def test_mapcore_get_extended_group_info(self, mock_get):
        from nii.mapcore import mapcore_get_extended_group_info

        group_key = 'fake_group_key'

        def func_get(url, **kwargs):
            res = requests.Response()
            res.status_code = requests.codes.ok
            if url.endswith('/group/' + group_key):
                res._content = '{"result": {"groups": [{"group_key": "' + group_key + '"}]}, "status": {"error_code": 0} }'
            elif url.endswith('/member/' + group_key):
                res._content = '{"result": {"accounts": [{"eppn": "' + self.me.eppn + '", "admin": 1 }]}, "status": {"error_code": 0} }'
            return res

        mock_get.side_effect = func_get

        mapcore_get_extended_group_info(self.me, self.project, group_key, base_grp=None)
        assert_equal(mock_get.call_count, 2)
        args, kwargs = mock_get.call_args_list[0]
        assert_equal(args[0].endswith('/group/' + group_key), True)
        args, kwargs = mock_get.call_args_list[1]
        assert_equal(args[0].endswith('/member/' + group_key), True)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('requests.post')
    def test_mapcore_add_to_group(self, mock_post):
        from nii.mapcore import mapcore_add_to_group

        group_key = 'fake_group_key'
        add_to_group = requests.Response()
        add_to_group.status_code = requests.codes.ok
        add_to_group._content = '{"result": {}, "status": {"error_code": 0} }'
        mock_post.return_value = add_to_group

        self.project.map_group_key = group_key
        self.project.save()

        mapcore_add_to_group(self.me, self.project, group_key, self.me.eppn, MAPCore.MODE_ADMIN)
        args, kwargs = mock_post.call_args
        assert_equal(args[0].endswith('/member/' + self.project.map_group_key + '/' + self.me.eppn), True)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('requests.delete')
    def test_mapcore_remove_from_group(self, mock_delete):
        from nii.mapcore import mapcore_remove_from_group

        group_key = 'fake_group_key'
        remove_from_group = requests.Response()
        remove_from_group.status_code = requests.codes.ok
        remove_from_group._content = '{"result": {}, "status": {"error_code": 0} }'
        mock_delete.return_value = remove_from_group

        self.project.map_group_key = group_key
        self.project.save()

        mapcore_remove_from_group(self.me, self.project, group_key, self.me.eppn)
        args, kwargs = mock_delete.call_args
        assert_equal(args[0].endswith('/member/' + self.project.map_group_key + '/' + self.me.eppn), True)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore_api.MAPCore.remove_from_group')
    @mock.patch('nii.mapcore_api.MAPCore.add_to_group')
    def test_mapcore_edit_member(self, mock_add, mock_remove):
        from nii.mapcore import mapcore_edit_member

        group_key = 'fake_group_key'
        mapcore_edit_member(self.me, self.project, group_key, self.me.eppn, MAPCore.MODE_ADMIN)
        assert_equal(mock_remove.call_count, 1)
        assert_equal(mock_add.call_count, 1)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_extended_group_info')
    def test_sync_rdm_project_title_desc(self, mock_get_grinfo):
        from nii.mapcore import mapcore_sync_rdm_project

        group_key = 'fake_group_key'
        r = randstr(4)
        group_name = r + '+' + self.project.title
        introduction = r + '+' + self.project.description

        mock_get_grinfo.return_value = {
            'group_key': group_key, 'group_name': group_name,
            'introduction': introduction,
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER,
                 'is_admin': False}]}
        with mock.patch('osf.models.node.AbstractNode.add_contributor') as mock_add, \
             mock.patch('osf.models.node.AbstractNode.remove_contributor') as mock_remove, \
             mock.patch('osf.models.node.AbstractNode.set_permissions') as mock_edit:
            mapcore_sync_rdm_project(self.me, self.project,
                                     title_desc=True, contributors=False,
                                     use_raise=True)
            assert_equal(mock_get_grinfo.call_count, 1)
            assert_equal(mock_add.call_count, 0)
            assert_equal(mock_remove.call_count, 0)
            assert_equal(mock_edit.call_count, 0)
        node2 = AbstractNode.objects.get(guids___id=self.project._id)
        assert_equal(node2.title, group_name)
        assert_equal(node2.description, introduction)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_extended_group_info')
    def test_sync_rdm_project_contributors(self, mock_get_grinfo):
        from nii.mapcore import mapcore_sync_rdm_project
        group_key = 'fake_group_key'

        # test #1 : same member list
        mock_get_grinfo.return_value = {
            'group_key': group_key, 'group_name': 'fake_group_name',
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER,
                 'is_admin': False}]}
        self.project.map_group_key = group_key
        self.project.add_contributor(self.user2, DEFAULT_CONTRIBUTOR_PERMISSIONS, save=False)
        self.project.save()
        with mock.patch('osf.models.node.AbstractNode.add_contributor') as mock_add, \
             mock.patch('osf.models.node.AbstractNode.remove_contributor') as mock_remove, \
             mock.patch('osf.models.node.AbstractNode.set_permissions') as mock_edit:
            mapcore_sync_rdm_project(self.me, self.project,
                                     title_desc=False, contributors=True,
                                     use_raise=True)
            assert_equal(mock_get_grinfo.call_count, 1)
            assert_equal(mock_add.call_count, 0)
            assert_equal(mock_remove.call_count, 0)
            assert_equal(mock_edit.call_count, 0)
        mock_get_grinfo.call_count = 0

        # test #2 : remove
        mock_get_grinfo.return_value = {
            'group_key': group_key, 'group_name': 'fake_group_name',
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True}]}
        with mock.patch('osf.models.node.AbstractNode.add_contributor') as mock_add, \
             mock.patch('osf.models.node.AbstractNode.remove_contributor') as mock_remove, \
             mock.patch('osf.models.node.AbstractNode.set_permissions') as mock_edit:
            mapcore_sync_rdm_project(self.me, self.project,
                                     title_desc=False, contributors=True,
                                     use_raise=True)
            assert_equal(mock_get_grinfo.call_count, 1)
            assert_equal(mock_add.call_count, 0)
            assert_equal(mock_remove.call_count, 1)
            assert_equal(mock_edit.call_count, 0)
        mock_get_grinfo.call_count = 0
        self.project.remove_contributor(self.user2, auth=Auth(self.me))
        self.project.save()

        # test #3 : add
        mock_get_grinfo.return_value = {
            'group_key': group_key, 'group_name': 'fake_group_name',
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER,
                 'is_admin': False}]}
        with mock.patch('osf.models.node.AbstractNode.add_contributor') as mock_add, \
             mock.patch('osf.models.node.AbstractNode.remove_contributor') as mock_remove, \
             mock.patch('osf.models.node.AbstractNode.set_permissions') as mock_edit:
            mapcore_sync_rdm_project(self.me, self.project,
                                     title_desc=False, contributors=True,
                                     use_raise=True)
            assert_equal(mock_get_grinfo.call_count, 1)
            assert_equal(mock_add.call_count, 1)
            assert_equal(mock_remove.call_count, 0)
            assert_equal(mock_edit.call_count, 0)
        mock_get_grinfo.call_count = 0

        # test #4 : set DEFAULT_CONTRIBUTOR_PERMISSIONS
        mock_get_grinfo.return_value = {
            'group_key': group_key, 'group_name': 'fake_group_name',
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER,
                 'is_admin': False}]}
        self.project.add_contributor(self.user2, CREATOR_PERMISSIONS, save=False)
        self.project.save()
        with mock.patch('osf.models.node.AbstractNode.add_contributor') as mock_add, \
             mock.patch('osf.models.node.AbstractNode.remove_contributor') as mock_remove, \
             mock.patch('osf.models.node.AbstractNode.set_permissions') as mock_edit:
            mapcore_sync_rdm_project(self.me, self.project,
                                     title_desc=False, contributors=True,
                                     use_raise=True)
            assert_equal(mock_get_grinfo.call_count, 1)
            assert_equal(mock_add.call_count, 0)
            assert_equal(mock_remove.call_count, 0)
            assert_equal(mock_edit.call_count, 1)
            args, kwargs = mock_edit.call_args
            assert_equal(args[0].eppn, self.user2.eppn)
            assert_equal(args[1], DEFAULT_CONTRIBUTOR_PERMISSIONS)
        mock_get_grinfo.call_count = 0

        # test #5 : set CREATOR_PERMISSIONS
        mock_get_grinfo.return_value = {
            'group_key': group_key, 'group_name': 'fake_group_name',
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True},
                {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True}]}
        self.project.set_permissions(self.user2, DEFAULT_CONTRIBUTOR_PERMISSIONS, save=False)
        self.project.save()
        with mock.patch('osf.models.node.AbstractNode.add_contributor') as mock_add, \
             mock.patch('osf.models.node.AbstractNode.remove_contributor') as mock_remove, \
             mock.patch('osf.models.node.AbstractNode.set_permissions') as mock_edit:
            mapcore_sync_rdm_project(self.me, self.project,
                                     title_desc=False, contributors=True,
                                     use_raise=True)
            assert_equal(mock_get_grinfo.call_count, 1)
            assert_equal(mock_add.call_count, 0)
            assert_equal(mock_remove.call_count, 0)
            assert_equal(mock_edit.call_count, 1)
            args, kwargs = mock_edit.call_args
            assert_equal(args[0].eppn, self.user2.eppn)
            assert_equal(args[1], CREATOR_PERMISSIONS)

        self.project.remove_contributor(self.user2, auth=Auth(self.me))
        self.project.save()

    @mock.patch('nii.mapcore.mapcore_sync_rdm_project0')
    def test_sync_rdm_project_error(self, mock_sync):
        from nii.mapcore import mapcore_sync_rdm_project

        mock_sync.side_effect = Exception('fake error message')
        mapcore_sync_rdm_project(self.me, self.project, use_raise=False)
        assert_equal(mock_sync.call_count, 1)
        node_copy = AbstractNode.objects.get(guids___id=self.project._id)
        assert_equal(node_copy.logs.latest().action,
                     NodeLog.MAPCORE_RDM_PROJECT_NOT_UPDATED)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_extended_group_info')
    @mock.patch('osf.models.node.AbstractNode.add_contributor')
    @mock.patch('osf.models.node.AbstractNode.remove_contributor')
    @mock.patch('osf.models.node.AbstractNode.set_permissions')
    def test_sync_rdm_ignore_unregistered_osfuser(self, mock_edit, mock_remove, mock_add, mock_get_grinfo):
        from nii.mapcore import mapcore_sync_rdm_project

        mock_get_grinfo.return_value = {
            'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
            'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
            'group_member_list': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                 'is_admin': True},
                {'eppn': 'UNKNOWN_USER+' + self.user2.eppn,
                 'admin': MAPCore.MODE_MEMBER, 'is_admin': False}]}
        mapcore_sync_rdm_project(self.me, self.project,
                                 title_desc=False, contributors=True,
                                 use_raise=True)
        assert_equal(mock_get_grinfo.call_count, 1)
        assert_equal(mock_add.call_count, 0)  # not called
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 0)
        node_copy = AbstractNode.objects.get(guids___id=self.project._id)
        assert_equal(node_copy.logs.latest().action,
                     NodeLog.MAPCORE_RDM_UNKNOWN_USER)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_get_group_by_key')
    @mock.patch('nii.mapcore.mapcore_get_group_members')
    @mock.patch('osf.models.node.AbstractNode.add_contributor')
    @mock.patch('osf.models.node.AbstractNode.remove_contributor')
    @mock.patch('osf.models.node.AbstractNode.set_permissions')
    def test_sync_rdm_ignore_unconfirmed_invited_member(self, mock_edit, mock_remove, mock_add, mock_get_members, mock_get_group):
        from nii.mapcore import mapcore_sync_rdm_project

        mock_get_group.return_value = {
            'result': {'groups': [{
                'group_key': 'fake_group_key', 'group_name': 'fake_group_name',
                'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC}]}}
        mock_get_members.return_value = {
            'result': {'accounts': [
                {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN},
                {'eppn': None, 'admin': MAPCore.MODE_MEMBER},
                {'admin': MAPCore.MODE_MEMBER},
                {}]}}
        mapcore_sync_rdm_project(self.me, self.project,
                                 title_desc=False, contributors=True,
                                 use_raise=True)
        assert_equal(mock_get_group.call_count, 1)
        assert_equal(mock_get_members.call_count, 1)
        assert_equal(mock_add.call_count, 0)
        assert_equal(mock_remove.call_count, 0)
        assert_equal(mock_edit.call_count, 0)

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore_api.MAPCore.get_my_groups')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project')
    def test_sync_rdm_my_projects(self, mock_sync_rdm, mock_or, mock_mygr):
        from django.core.exceptions import ObjectDoesNotExist
        from nii.mapcore import mapcore_sync_rdm_my_projects

        # test #1 : same groups, same title
        mock_mygr.return_value = {
            'result': {'groups': [
                {'group_name': 'fake_group_name1',
                 'group_key': 'fake_group_key1',
                 'active': 1, 'public': 1,
                 'open_member': OPEN_MEMBER_PUBLIC}]}}
        self.project.title = 'fake_group_name1'
        self.project.map_group_key = 'fake_group_key1'
        self.project.save()
        mapcore_sync_rdm_my_projects(self.me, use_raise=True)
        assert_equal(mock_mygr.call_count, 1)
        assert_equal(mock_or.call_count, 0)
        assert_equal(mock_sync_rdm.call_count, 0)
        mock_mygr.call_count = 0

        # test #2 : same groups, different title
        self.project.title = 'fake_group_name1' + randstr(4)
        self.project.save()
        mapcore_sync_rdm_my_projects(self.me, use_raise=True)
        assert_equal(mock_mygr.call_count, 1)
        assert_equal(mock_or.call_count, 1)
        assert_equal(mock_sync_rdm.call_count, 0)
        mock_mygr.call_count = 0
        mock_or.call_count = 0

        # test #3 : mAP group only, RDM project exists
        mock_mygr.return_value = {
            'result': {'groups': [
                {'group_name': 'fake_group_name1',
                 'group_key': 'fake_group_key1',
                 'active': 1, 'public': 1,
                 'open_member': OPEN_MEMBER_PUBLIC},
                {'group_name': 'fake_group_name2',
                 'group_key': 'fake_group_key2',
                 'active': 1, 'public': 1,
                 'open_member': OPEN_MEMBER_PUBLIC}]}}
        self.project.title = 'fake_group_name1'
        self.project.save()
        project2 = ProjectFactory(
            creator=self.user2,
            is_public=True,
            title='fake_group_name2'
        )
        project2.map_group_key = 'fake_group_key2'
        project2.save()  # self.me is not a member.
        mapcore_sync_rdm_my_projects(self.me, use_raise=True)
        assert_equal(mock_mygr.call_count, 1)
        assert_equal(mock_or.call_count, 1)
        assert_equal(mock_sync_rdm.call_count, 0)
        mock_mygr.call_count = 0
        mock_or.call_count = 0
        project2.delete()

        # test #4 : mAP group only, RDM project does not exist
        mock_mygr.return_value = {
            'result': {'groups': [
                {'group_name': 'fake_group_name1',
                 'group_key': 'fake_group_key1',
                 'active': 1, 'public': 1,
                 'open_member': OPEN_MEMBER_PUBLIC},
                {'group_name': 'fake_group_name2',
                 'group_key': 'fake_group_key2',
                 'active': 1, 'public': 1,
                 'open_member': OPEN_MEMBER_PUBLIC}]}}
        # self.project.title = 'fake_group_name1'
        # self.project.map_group_key = 'fake_group_key1'
        # self.project.save()
        with assert_raises(ObjectDoesNotExist):
            AbstractNode.objects.get(map_group_key='fake_group_key2')
        with mock.patch('nii.mapcore.mapcore_get_extended_group_info') as mock_gi:
            mock_gi.return_value = {
                'group_name': 'fake_group_name2',
                'group_key': 'fake_group_key2',
                'introduction': 'fake_introduction2',
                'active': 1, 'public': 1, 'open_member': OPEN_MEMBER_PUBLIC,
                'group_admin_eppn': [self.me.eppn],
                'group_member_list': [
                    {'eppn': self.me.eppn, 'admin': MAPCore.MODE_ADMIN,
                     'is_admin': True},
                    {'eppn': self.user2.eppn, 'admin': MAPCore.MODE_MEMBER,
                     'is_admin': False}]}
            mapcore_sync_rdm_my_projects(self.me, use_raise=True)
            assert_equal(mock_gi.call_count, 1)
            assert_equal(mock_mygr.call_count, 1)
            assert_equal(mock_or.call_count, 0)
            assert_equal(mock_sync_rdm.call_count, 1)
        n = AbstractNode.objects.get(map_group_key='fake_group_key2')
        assert_equal(n.is_public, False)
        assert_equal(n.title, 'fake_group_name2')
        assert_equal(n.map_group_key, 'fake_group_key2')
        assert_equal(n.description, 'fake_introduction2')
        n.delete()
        mock_mygr.call_count = 0
        mock_sync_rdm.call_count = 0

        # test #5 : RDM project only, no map_group_key
        mock_mygr.return_value = {'result': {'groups': []}}
        self.project.title = 'fake_group_name1'
        self.project.map_group_key = None
        self.project.save()
        mapcore_sync_rdm_my_projects(self.me, use_raise=True)
        assert_equal(mock_mygr.call_count, 1)
        assert_equal(mock_or.call_count, 0)  # not called
        assert_equal(mock_sync_rdm.call_count, 0)
        mock_mygr.call_count = 0

        # test #6 : RDM project only, has map_group_key
        mock_mygr.return_value = {'result': {'groups': []}}
        self.project.title = 'fake_group_name1'
        self.project.map_group_key = 'fake_group_key1'
        self.project.save()
        mapcore_sync_rdm_my_projects(self.me, use_raise=True)
        assert_equal(mock_mygr.call_count, 1)
        assert_equal(mock_or.call_count, 1)
        assert_equal(mock_sync_rdm.call_count, 0)
        mock_mygr.call_count = 0

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project0')
    def test_mapcore_sync_rdm_project_no_map_group(self, mock_sync):
        from nii.mapcore import mapcore_sync_rdm_project
        from nii.mapcore_api import MAPCore, MAPCoreException

        project2 = ProjectFactory(
            creator=self.me,
            is_public=True,
            title='fake_group_name2'
        )
        project2.map_group_key = 'fake_group_key2'
        project2.save()
        assert_equal(project2.is_deleted, False)

        m = MAPCore(self.me)
        m.api_error_code = 208
        m.error_message = 'You do not have access permission'
        mock_sync.side_effect = MAPCoreException(m, None)
        mapcore_sync_rdm_project(self.me, project2,
                                 title_desc=True, contributors=True,
                                 use_raise=True)
        # reload
        project2a = AbstractNode.objects.get(guids___id=project2._id)
        assert_equal(project2a.is_deleted, True)
        project2a.delete()

    @mock.patch('nii.mapcore_api.MAPCORE_SECRET', 'fake_secret')
    @mock.patch('nii.mapcore_api.MAPCORE_HOSTNAME', 'fake_hostname')
    @mock.patch('nii.mapcore_api.MAPCORE_API_PATH', '/fake_api_path')
    @mock.patch('requests.get')
    def test_mapcore_get_my_groups(self, mock_get):
        res = requests.Response()
        res.status_code = requests.codes.ok
        res._content = '{"result": {"groups": [ {"group_name": "fake_group_name1", "group_key": "fake_group_key1", "active": 1, "public": 1, "open_member": 1} ] }, "status": {"error_code": 0} }'
        mock_get.return_value = res
        mapcore = MAPCore(self.me)
        mapcore.get_my_groups()
        args, kwargs = mock_get.call_args
        assert_equal(args[0].endswith('/mygroup'), True)


@pytest.mark.django_db
class TestViewsWithMAPCore(OsfTestCase):
    def setUp(self):
        mapcore_disable_log()
        OsfTestCase.setUp(self)
        self.me = AuthUserFactory()
        self.me.eppn = fake_email()
        BookmarkCollectionFactory(creator=self.me)
        self.project = ProjectFactory(
            creator=self.me,
            is_public=True,
            title=fake.bs()
        )
        self.project_url = self.project.web_url_for('view_project')
        self.user2 = AuthUserFactory()
        self.project.add_contributor(self.user2, auth=Auth(self.me))
        self.project.save()

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_dashboard')
    @mock.patch('website.views.use_ember_app')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    @mock.patch('website.mapcore.views.mapcore_request_authcode')
    def test_dashboard_without_token(self, mock_ac, mock_sync, mock_ember):
        mapcore = MAPCore(self.me)
        mock_sync.side_effect = MAPCoreTokenExpired(mapcore, 'test message')

        url = web_url_for('dashboard', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 302)
        assert_equal(mock_sync.call_count, 1)
        assert_equal(mock_ember.call_count, 0)
        mapcore_oauth_start_url = web_url_for('mapcore_oauth_start')
        assert_in(mapcore_oauth_start_url + '?next_url=',
                  res.headers.get('Location'))
        res2 = res.follow(auth=self.me.auth)
        assert_equal(mock_ac.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_my_projects')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    @mock.patch('website.mapcore.views.mapcore_request_authcode')
    def test_my_projects_without_token(self, mock_ac, mock_sync):
        mapcore = MAPCore(self.me)
        mock_sync.side_effect = MAPCoreTokenExpired(mapcore, 'test message')

        url = web_url_for('my_projects', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 302)
        assert_equal(mock_sync.call_count, 1)
        mapcore_oauth_start_url = web_url_for('mapcore_oauth_start')
        assert_in(mapcore_oauth_start_url + '?next_url=',
                  res.headers.get('Location'))
        res2 = res.follow(auth=self.me.auth)
        assert_equal(mock_ac.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_view_project')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    @mock.patch('website.mapcore.views.mapcore_request_authcode')
    def test_view_project_without_token(self, mock_ac, mock_sync2, mock_sync1):
        mapcore = MAPCore(self.me)
        mock_sync2.side_effect = MAPCoreTokenExpired(mapcore, 'test message')

        res = self.app.get(self.project_url, auth=self.me.auth)
        assert_equal(res.status_code, 302)
        assert_equal(mock_sync1.call_count, 0)
        assert_equal(mock_sync2.call_count, 1)
        mapcore_oauth_start_url = web_url_for('mapcore_oauth_start')
        assert_in(mapcore_oauth_start_url + '?next_url=',
                  res.headers.get('Location'))
        res2 = res.follow(auth=self.me.auth)
        assert_equal(mock_ac.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_dashboard')
    @mock.patch('website.views.use_ember_app')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    def test_dashboard(self, mock_sync, mock_ember):
        url = web_url_for('dashboard', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 1)
        assert_equal(mock_ember.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_my_projects')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    def test_my_projects(self, mock_sync):
        url = web_url_for('my_projects', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_view_project')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    #@mock.patch('framework.auth.decorators.mapcore_sync_rdm_project_or_map_group')  # cannot hook
    def test_view_project(self, mock_sync2, mock_sync1):
        res = self.app.get(self.project_url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync1.call_count, 2)  # at decorator.py and _view_project()
        assert_equal(mock_sync2.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_dashboard_disabled')
    @mock.patch('website.views.use_ember_app')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    def test_dashboard_disabled(self, mock_sync, mock_ember):
        mapcore_sync_set_disabled()
        url = web_url_for('dashboard', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 0)
        assert_equal(mock_ember.call_count, 1)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_my_projects_disabled')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_my_projects0')
    def test_my_projects_disabled(self, mock_sync):
        mapcore_sync_set_disabled()
        url = web_url_for('my_projects', _absolute=True)
        res = self.app.get(url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync.call_count, 0)

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_view_project_disabled')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    def test_view_project_disabled(self, mock_sync2, mock_sync1):
        mapcore_sync_set_disabled()
        res = self.app.get(self.project_url, auth=self.me.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_sync1.call_count, 0)
        assert_equal(mock_sync2.call_count, 0)

    ### from tests/test_views.py::test_edit_node_title
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_edit_node_title')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    def test_edit_node_title(self, mock_sync3, mock_sync2, mock_sync1):
        url = '/api/v1/project/{0}/edit/'.format(self.project._id)
        # The title is changed though posting form data
        self.app.post_json(url, {'name': 'title', 'value': 'Bacon'},
                           auth=self.me.auth).maybe_follow()
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        assert_equal(mock_sync3.call_count, 1)
        self.project.reload()
        # The title was changed
        assert_equal(self.project.title, 'Bacon')
        # A log event was saved
        assert_equal(self.project.logs.latest().action, 'edit_title')

    ### from tests/test_views.py::test_edit_description
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_edit_description')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    def test_edit_description(self, mock_sync3, mock_sync2, mock_sync1):
        url = '/api/v1/project/{0}/edit/'.format(self.project._id)
        self.app.post_json(url,
                           {'name': 'description', 'value': 'Deep-fried'},
                           auth=self.me.auth)
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        assert_equal(mock_sync3.call_count, 1)
        self.project.reload()
        assert_equal(self.project.description, 'Deep-fried')

    ### from tests/test_views.py::test_add_contributor_post
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_add_contributors')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    def test_add_contributors(self, mock_sync3, mock_sync2, mock_sync1):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.me, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()
        url = '/api/v1/project/{0}/contributors/'.format(project._id)

        dict2 = add_contributor_json(user2)
        dict3 = add_contributor_json(user3)
        dict2.update({
            'permission': 'admin',
            'visible': True,
        })
        dict3.update({
            'permission': 'write',
            'visible': False,
        })

        self.app.post_json(
            url,
            {
                'users': [dict2, dict3],
                'node_ids': [project._id],
            },
            content_type='application/json',
            auth=self.me.auth,
        ).maybe_follow()
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        assert_equal(mock_sync3.call_count, 1)
        project.reload()
        assert_in(user2, project.contributors)
        # A log event was added
        assert_equal(project.logs.latest().action, 'contributor_added')
        assert_equal(len(project.contributors), 3)

        assert_equal(project.get_permissions(user2), ['read', 'write', 'admin'])
        assert_equal(project.get_permissions(user3), ['read', 'write'])

    ### from tests/test_views.py::test_contributor_manage_reorder
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_contributor_manage_reorder')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    def test_contributor_manage_reorder(self, mock_sync3, mock_sync2, mock_sync1):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.me, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        from osf.utils import permissions
        project.add_contributors(
            [
                {'user': reg_user1,
                 'permissions': permissions.ADMIN, 'visible': True},
                {'user': reg_user2,
                 'permissions': permissions.ADMIN, 'visible': False},
            ]
        )
        # Add a non-registered user
        unregistered_user = project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=Auth(self.me),
            save=True,
        )

        url = project.api_url + 'contributors/manage/'
        self.app.post_json(
            url,
            {
                'contributors': [
                    {'id': reg_user2._id,
                     'permission': permissions.ADMIN,
                     'registered': True, 'visible': False},
                    {'id': project.creator._id,
                     'permission': permissions.ADMIN,
                     'registered': True, 'visible': True},
                    {'id': unregistered_user._id,
                     'permission': permissions.ADMIN,
                     'registered': False, 'visible': True},
                    {'id': reg_user1._id,
                     'permission': permissions.ADMIN,
                     'registered': True, 'visible': True},
                ]
            },
            auth=self.me.auth,
        )
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        assert_equal(mock_sync3.call_count, 1)
        project.reload()
        assert_equal(
            # Note: Cast ForeignList to list for comparison
            list(project.contributors),
            [reg_user2, project.creator, unregistered_user, reg_user1]
        )
        assert_equal(
            list(project.visible_contributors),
            [project.creator, unregistered_user, reg_user1]
        )

    ### from tests/test_views.py::test_project_remove_contributor
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_remove_contributor')
    @mock.patch('nii.mapcore.mapcore_sync_rdm_project_or_map_group0')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    @mock.patch('nii.mapcore.mapcore_api_is_available0')
    def test_remove_contributor(self, mock_sync3, mock_sync2, mock_sync1):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id]}
        self.app.post(url, json.dumps(payload),
                      content_type='application/json',
                      auth=self.me.auth).maybe_follow()
        assert_equal(mock_sync1.call_count, 1)
        assert_equal(mock_sync2.call_count, 1)
        assert_equal(mock_sync3.call_count, 1)
        self.project.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs.latest().action, 'contributor_removed')


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestOSFAPIWithMAPCore:

    @pytest.fixture(autouse=True, scope='class')
    def app_init(self):
        mapcore_disable_log()
        #DEBUG('*** app_init')
        from website.app import init_app
        init_app(routes=False, set_backends=False)

    @pytest.fixture()
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_one(self, institution_one):
        auth_user = AuthUserFactory()
        auth_user.affiliated_institutions.add(institution_one)
        return auth_user

    @pytest.fixture()
    def nodes_url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def title(self):
        return 'GRDM Project'

    @pytest.fixture()
    def title_new(self):
        return 'Super GRDM Project'

    @pytest.fixture()
    def description(self):
        return 'Pytest conversions are tedious'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def private_project(self, user_one, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user_one
        )

    @pytest.fixture()
    def private_project_json(self, title, description, category):
        return {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': False
                }
            }
        }

    ### from api_tests/nodes/views/test_node_list.py::
    ###      test_creates_private_project_logged_in_contributor
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_create_project')
    @mock.patch('nii.mapcore.mapcore_sync_map_new_group0')
    def test_create_project(
            self, mock_sync, app, user_one, private_project_json, nodes_url):
        res = app.post_json_api(nodes_url, private_project_json, auth=user_one.auth)
        assert_equal(mock_sync.call_count, 1)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == private_project_json['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == private_project_json['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == private_project_json['data']['attributes']['category']
        pid = res.json['data']['id']
        project = AbstractNode.load(pid)
        assert project.logs.latest().action == NodeLog.PROJECT_CREATED

    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_create_project_error')
    @mock.patch('nii.mapcore.mapcore_sync_map_new_group0')
    def test_create_project_error(
            self, mock_sync, app, user_one, private_project_json, nodes_url):
        mock_sync.side_effect = Exception('fake error message')
        res = app.post_json_api(nodes_url, private_project_json, auth=user_one.auth)
        # Node creation: no error
        assert_equal(mock_sync.call_count, 1)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == private_project_json['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == private_project_json['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == private_project_json['data']['attributes']['category']
        pid = res.json['data']['id']
        project = AbstractNode.load(pid)
        # mAP core group creation: error
        assert project.logs.latest().action == NodeLog.MAPCORE_MAP_GROUP_NOT_CREATED

    ### from api_tests/nodes/views/test_node_detail.py::
    ###      test_partial_update_private_project_logged_in_contributor
    @mock.patch('nii.mapcore.MAPCORE_CLIENTID', 'test_update_project')
    @mock.patch('nii.mapcore.mapcore_sync_map_group0')
    def test_update_project(
            self, mock_sync, app, user_one, title_new, description, category, private_project, private_url):
        with assert_latest_log(NodeLog.EDITED_TITLE, private_project):
            res = app.patch_json_api(private_url, {
                'data': {
                    'attributes': {
                        'title': title_new},
                    'id': private_project._id,
                    'type': 'nodes',
                }
            }, auth=user_one.auth)
            assert_equal(mock_sync.call_count, 1)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == title_new
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

# refer to tests/test_views.py:TestAuthViews
@pytest.mark.enable_quickfiles_creation
class TestAuthViewsLoginByEppn(OsfTestCase):

    def setUp(self):
        super(TestAuthViewsLoginByEppn, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    @mock.patch('website.views.use_ember_app')
    def test_new_user_and_set_email(self, mock_ember):
        self.user.have_email = False  # new user
        self.user.save()

        ### redirect to user_account_email
        url = web_url_for('dashboard', _absolute=True)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 302)
        user_account_email_url = web_url_for('user_account_email')
        assert_in(user_account_email_url, res.headers.get('Location'))

        ### set email
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token, self.user.username)
        res = self.app.get(url)
        assert_equal(res.status_code, 302)
        cas_redirect_url = '{}/logout?service={}/login?service={}myprojects/'.format(settings.CAS_SERVER_URL, settings.CAS_SERVER_URL, settings.DOMAIN)
        assert_in(cas_redirect_url, res.headers.get('Location'))

        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], True)
        email_verifications = self.user.unconfirmed_email_info
        assert_equal(email_verifications[0]['address'], 'test@mail.com')

        url = web_url_for('dashboard', _absolute=True)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(mock_ember.call_count, 1)

    @mock.patch('website.mapcore.views.mapcore_receive_authcode')
    def test_mapcore_oauth_complete(self, mock):
        url = web_url_for('mapcore_oauth_complete')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 302)
        assert_equal(mock.call_count, 1)
