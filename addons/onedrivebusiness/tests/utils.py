# -*- coding: utf-8 -*-
import mock
from nose.tools import (assert_equals, assert_true, assert_false)
from openpyxl import Workbook

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.onedrivebusiness.tests.factories import OneDriveBusinessAccountFactory
from addons.onedrivebusiness.models import OneDriveBusinessProvider
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer
from addons.onedrivebusiness import utils

class OneDriveBusinessAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'onedrivebusiness'
    ExternalAccountFactory = OneDriveBusinessAccountFactory
    Provider = OneDriveBusinessProvider
    Serializer = OneDriveBusinessSerializer
    client = None
    folder = {
        'path': 'bucket',
        'name': 'bucket',
        'id': 'bucket'
    }

    def test_get_region_external_account_no_institutions(self):
        mock_node = mock.Mock()
        mock_user = mock.Mock()
        mock_affiliated_institutions = mock.Mock()
        mock_institutions_first = mock.Mock()
        mock_institutions_first.return_value = None
        mock_affiliated_institutions.first = mock_institutions_first
        mock_user.affiliated_institutions = mock_affiliated_institutions
        mock_node.creator = mock_user

        ret = utils.get_region_external_account(mock_node)
        assert_equals(ret, None)

    @mock.patch('addons.onedrivebusiness.utils.RdmAddonOption.objects.filter')
    def test_get_region_external_account_with_unconfigured_institutions(
        self,
        mock_rdm_addon_option_objects_filter
    ):
        mock_node = mock.Mock()
        mock_user = mock.Mock()
        mock_affiliated_institutions = mock.Mock()
        mock_institution = mock.Mock()
        mock_institution.id = 1234
        mock_institutions_first = mock.Mock()
        mock_institutions_first.return_value = mock_institution
        mock_affiliated_institutions.first = mock_institutions_first
        mock_user.affiliated_institutions = mock_affiliated_institutions
        mock_node.creator = mock_user

        mock_rdm_addon_option_objects = mock.Mock()
        mock_rdm_addon_option_objects_first = mock.Mock()
        mock_rdm_addon_option_objects_first.return_value = None
        mock_rdm_addon_option_objects.first = mock_rdm_addon_option_objects_first
        mock_rdm_addon_option_objects_filter.return_value = mock_rdm_addon_option_objects

        ret = utils.get_region_external_account(mock_node)
        assert_equals(ret, None)
        mock_rdm_addon_option_objects_filter.assert_has_calls([
            mock.call(institution_id=1234, is_allowed=True, provider='onedrivebusiness'),
        ])

    @mock.patch('addons.onedrivebusiness.utils.RdmAddonOption.objects.filter')
    @mock.patch('addons.onedrivebusiness.utils.Region.objects.get')
    @mock.patch('addons.onedrivebusiness.utils.RegionExternalAccount.objects.get')
    def test_get_region_external_account_with_configured_institutions(
        self,
        mock_region_external_account_objects_get,
        mock_region_objects_get,
        mock_rdm_addon_option_objects_filter
    ):
        mock_node = mock.Mock()
        mock_user = mock.Mock()
        mock_affiliated_institutions = mock.Mock()
        mock_institution = mock.Mock()
        mock_institution.id = 1234
        mock_institutions_first = mock.Mock()
        mock_institutions_first.return_value = mock_institution
        mock_affiliated_institutions.first = mock_institutions_first
        mock_user.affiliated_institutions = mock_affiliated_institutions
        mock_node.creator = mock_user

        mock_rdm_addon_option_object = mock.Mock()
        mock_rdm_addon_option_objects = mock.Mock()
        mock_rdm_addon_option_objects_first = mock.Mock()
        mock_rdm_addon_option_objects_first.return_value = mock_rdm_addon_option_object
        mock_rdm_addon_option_objects.first = mock_rdm_addon_option_objects_first
        mock_rdm_addon_option_objects_filter.return_value = mock_rdm_addon_option_objects

        mock_region_object = mock.Mock()
        mock_region_objects_get.return_value = mock_region_object
        mock_region_external_account_objects_get.return_value = {'test': True}

        ret = utils.get_region_external_account(mock_node)
        assert_true(ret is not None)
        assert_true(ret['test'])

    @mock.patch('addons.onedrivebusiness.utils.UserListClient.get_workbook_sheet')
    def test_get_user_map(self, mock_get_workbook_sheet):
        wb = Workbook()
        worksheet = wb.active
        worksheet['A1'] = 'ePPN'
        worksheet['B1'] = 'MicrosoftAccount'
        worksheet['A2'] = 'eppn1234'
        worksheet['B2'] = 'msaccount5678'
        worksheet['A3'] = '#ここにePPNを記述'
        worksheet['B3'] = '#ここにMicrosoftアカウントを記述'
        mock_get_workbook_sheet.return_value = worksheet

        user_map = utils.get_user_map(None, 'test_get_user_map_folder_1234')
        assert_equals(user_map, {'eppn1234': 'msaccount5678'})
