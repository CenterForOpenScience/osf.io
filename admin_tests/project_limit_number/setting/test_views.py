import json
import time
from http import HTTPStatus
from unittest.mock import patch

from django.db import DatabaseError
from django.test import RequestFactory
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from admin.base import settings
from admin.project_limit_number import utils
from admin_tests.utilities import setup_view
from osf_tests.factories import AuthUserFactory, InstitutionFactory, ProjectFactory
from admin.project_limit_number.setting.views import (
    LIST_VALUE_SETTING_TYPE_LIST,
    ProjectLimitNumberSettingListView,
    ProjectLimitNumberSettingDetailView,
    SaveProjectLimitNumberDefaultView,
    ProjectLimitNumberSettingSaveAvailabilityView,
    ProjectLimitNumberSettingCreateView,
    DeleteProjectLimitNumberSettingView,
    UpdateProjectLimitNumberSettingView,
    UserListView
)
from osf.models import (
    UserExtendedData,
    ProjectLimitNumberDefault,
    ProjectLimitNumberSetting,
    ProjectLimitNumberTemplate,
    ProjectLimitNumberSettingAttribute,
    ProjectLimitNumberTemplateAttribute
)
from tests.base import AdminTestCase


class TestProjectLimitNumberSettingListView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.template_patcher = patch('admin.project_limit_number.setting.views.render_bad_request_response')
        self.mock_render = self.template_patcher.start()
        self.mock_render.return_value.status_code = HTTPStatus.BAD_REQUEST
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create user
        self.user = AuthUserFactory()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template'
        )

        # Create base URL
        self.base_url = reverse('project_limit_number:settings:list-setting')

        # Create view class
        self.view = ProjectLimitNumberSettingListView()
        self.view.kwargs = {}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.get(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.get(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = self.request_factory.get(self.base_url)
        request.user = self.user
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

    def test_get_queryset(self):
        """Test queryset returns correct data"""
        setting = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            is_deleted=False,
            priority=1
        )

        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), setting)

    def test_get_context_data_super_admin(self):
        """Test context data for super admin"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        self.view.object_list = self.view.get_queryset()

        context = self.view.get_context_data()
        self.assertIn('institutions', context)
        self.assertIn(self.institution, context['institutions'])

    def test_get_context_data_institution_admin(self):
        """Test context data for institution admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.get(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)
        self.view.object_list = self.view.get_queryset()

        context = self.view.get_context_data()
        self.assertEqual(len(context['institutions']), 1)
        self.assertEqual(context['institutions'][0], self.institution)

    def test_get_context_data_invalid_institution_access(self):
        """Test access to invalid institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(self.institution)

        request = self.request_factory.get(f'{self.base_url}?institution_id={other_institution.id}')
        request.user = self.institution_admin
        self.view.kwargs = {'institution_id': other_institution.id}
        self.view = setup_view(self.view, request)
        self.view.object_list = self.view.get_queryset()

        with self.assertRaises(PermissionDenied):
            self.view.get_context_data()

    def test_get_context_data_pagination(self):
        """Test pagination functionality"""
        # Create multiple settings
        for i in range(15):
            ProjectLimitNumberSetting.objects.create(
                institution=self.institution,
                template=self.template,
                priority=i,
                is_deleted=False
            )

        request = self.request_factory.get(f'{self.base_url}?institution_id={self.institution.id}&page_size=10')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id, 'page_size': 10}
        self.view = setup_view(self.view, request)
        self.view.object_list = self.view.get_queryset()

        context = self.view.get_context_data()
        self.assertEqual(len(context['project_limit_number_setting_list']), 10)

    def test_get_context_data_default_limit_value(self):
        """Test default limit value in context"""
        ProjectLimitNumberDefault.objects.create(
            institution=self.institution,
            project_limit_number=5
        )

        request = self.request_factory.get(f'{self.base_url}?institution_id={self.institution.id}')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view = setup_view(self.view, request)
        self.view.object_list = self.view.get_queryset()

        context = self.view.get_context_data()
        self.assertEqual(context['project_limit_number_default_value'], 5)

    def test_get_invalid_institution_id_format(self):
        """Test with invalid institution_id format"""
        request = self.request_factory.get(f'{self.base_url}?institution_id=invalid')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': 'invalid'}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The institution id is invalid.'
        )

    def test_get_nonexistent_institution(self):
        """Test with non-existent institution"""
        request = self.request_factory.get(f'{self.base_url}?institution_id=-1')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': -1}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The institution not exist.'
        )

    def test_get_invalid_page_size_format(self):
        """Test with invalid page_size format"""
        request = self.request_factory.get(f'{self.base_url}?page_size=invalid')
        request.user = self.super_admin
        self.view.kwargs = {'page_size': 'invalid'}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The page size is invalid.'
        )

    def test_get_nonexistent_page_size(self):
        """Test with non-existent page_size"""
        request = self.request_factory.get(f'{self.base_url}?page_size=-1')
        request.user = self.super_admin
        self.view.kwargs = {'page_size': -1}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The page size is invalid.'
        )

    def test_get_successful(self):
        """Test successful GET request"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.mock_render.assert_not_called()


class TestSaveProjectLimitNumberDefaultView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create user
        self.user = AuthUserFactory()

        # Create base URL
        self.base_url = '/project-limit-number/default/save/'

        # Create view class
        self.view = SaveProjectLimitNumberDefaultView()
        self.view.kwargs = {}

        # Create valid request data
        self.valid_data = {
            'institution_id': self.institution.id,
            'project_limit_number': 5
        }

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.put(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.put(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = self.request_factory.put(self.base_url)
        request.user = self.user
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_put_invalid_json_body(self):
        """Test with invalid JSON in request body"""
        request = self.request_factory.put(
            self.base_url,
            data='invalid json',
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The request body is invalid.'}
        )

    def test_put_invalid_field(self):
        """Test with invalid field in request body"""
        data = self.valid_data.copy()
        data['invalid_field'] = 'invalid value'

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Unknown field is invalid.'}
        )

    def test_put_project_limit_number_exceeds_maximum(self):
        """Test with project limit number exceeding maximum allowed"""
        data = self.valid_data.copy()
        data['project_limit_number'] = settings.PROJECT_LIMIT_NUMBER + 1

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'project_limit_number is invalid.'}
        )

    def test_put_nonexistent_institution(self):
        """Test with non-existent institution"""
        data = self.valid_data.copy()
        data['institution_id'] = -1

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The institution not exist.'}
        )

    def test_put_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Forbidden'}
        )

    def test_put_create_new_default(self):
        """Test creating new project limit number default"""
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        default = ProjectLimitNumberDefault.objects.get(institution=self.institution)
        self.assertEqual(default.project_limit_number, self.valid_data['project_limit_number'])

    def test_put_update_existing_default(self):
        """Test updating existing project limit number default"""
        existing_default = ProjectLimitNumberDefault.objects.create(
            institution=self.institution,
            project_limit_number=3
        )

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        existing_default.refresh_from_db()
        self.assertEqual(existing_default.project_limit_number, self.valid_data['project_limit_number'])


class TestProjectLimitNumberSettingSaveAvailabilityView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create user
        self.user = AuthUserFactory()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template'
        )

        # Create settings
        self.setting1 = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            priority=1,
            is_availability=True,
            is_deleted=False
        )
        self.setting2 = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            priority=2,
            is_availability=True,
            is_deleted=False
        )

        # Create base URL
        self.base_url = '/project-limit-number/settings/save-availability/'

        # Create view class
        self.view = ProjectLimitNumberSettingSaveAvailabilityView()
        self.view.kwargs = {}

        # Create valid request data
        self.valid_data = {
            'institution_id': self.institution.id,
            'setting_list': [
                {
                    'id': self.setting1.id,
                    'priority': 2,
                    'is_availability': False
                },
                {
                    'id': self.setting2.id,
                    'priority': 1,
                    'is_availability': True
                }
            ]
        }

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.put(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.put(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.put(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = self.request_factory.put(self.base_url)
        request.user = self.user
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_put_invalid_json_body(self):
        """Test with invalid JSON in request body"""
        request = self.request_factory.put(
            self.base_url,
            data='invalid json',
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The request body is invalid.'}
        )

    def test_put_invalid_field(self):
        """Test with invalid field in request body"""
        data = self.valid_data.copy()
        data['invalid_field'] = 'invalid value'

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Unknown field is invalid.'}
        )

    def test_put_duplicate_setting_ids(self):
        """Test with duplicate setting IDs"""
        data = self.valid_data.copy()
        data['setting_list'] = [
            {
                'id': self.setting1.id,
                'priority': 1,
                'is_availability': True
            },
            {
                'id': self.setting1.id,  # Duplicate ID
                'priority': 2,
                'is_availability': False
            }
        ]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'id is invalid.'}
        )

    def test_put_duplicate_priorities(self):
        """Test with duplicate priorities"""
        data = self.valid_data.copy()
        data['setting_list'] = [
            {
                'id': self.setting1.id,
                'priority': 1,
                'is_availability': True
            },
            {
                'id': self.setting2.id,
                'priority': 1,  # Duplicate priority
                'is_availability': False
            }
        ]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'priority is invalid.'}
        )

    def test_put_nonexistent_institution(self):
        """Test with non-existent institution"""
        data = self.valid_data.copy()
        data['institution_id'] = -1

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The institution not exist.'}
        )

    def test_put_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Forbidden'}
        )

    def test_put_setting_not_exist(self):
        """Test with non-existent setting"""
        data = self.valid_data.copy()
        data['setting_list'].append(
            {
                'id': -1,
                'priority': 3,
                'is_availability': False
            }
        )

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The setting not exist.'}
        )

    def test_put_successful_update(self):
        """Test successful update of settings"""
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify updates
        self.setting1.refresh_from_db()
        self.setting2.refresh_from_db()

        self.assertEqual(self.setting1.priority, 2)
        self.assertEqual(self.setting2.priority, 1)
        self.assertFalse(self.setting1.is_availability)
        self.assertTrue(self.setting2.is_availability)

    def test_put_invalid_priority_value(self):
        """Test with invalid priority value"""
        data = self.valid_data.copy()
        data['setting_list'][0]['priority'] = 99  # Invalid priority

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The priority is invalid.'}
        )


class TestDeleteProjectLimitNumberSettingView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template',
            is_availability=True,
            is_deleted=False,
            used_setting_number=2
        )

        # Create settings
        self.setting1 = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Test Setting 1',
            priority=1,
            is_deleted=False
        )

        self.setting2 = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Test Setting 2',
            priority=2,
            is_deleted=False
        )

        # Create template attributes
        self.template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Test Attribute',
            setting_type=5,
            attribute_value='value1, value2, value3'
        )

        # Create setting attributes
        self.setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting1,
            attribute=self.template_attribute,
            attribute_value='test_value',
            is_deleted=False
        )

        # Create base URL
        self.base_url = f'/project-limit-number/settings/{self.setting1.id}/delete/'

        # Create view class
        self.view = DeleteProjectLimitNumberSettingView()
        self.view.kwargs = {'setting_id': self.setting1.id}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = RequestFactory().delete(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = RequestFactory().delete(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = RequestFactory().delete(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)
        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = RequestFactory().delete(self.base_url)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)
        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_delete_nonexistent_setting(self):
        """Test deleting non-existent setting"""
        request = RequestFactory().delete(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.delete(request, setting_id=-1)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The setting not exist.'}
        )

    def test_delete_already_deleted_setting(self):
        """Test deleting already deleted setting"""
        self.setting1.is_deleted = True
        self.setting1.save()

        request = RequestFactory().delete(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.delete(request, setting_id=self.setting1.id)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The setting not exist.'}
        )

    def test_delete_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)
        request = RequestFactory().delete(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        response = self.view.delete(request, setting_id=self.setting1.id)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Forbidden'}
        )

    def test_delete_successful(self):
        """Test successful deletion of setting"""
        request = RequestFactory().delete(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.delete(request, setting_id=self.setting1.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify setting was marked as deleted
        self.setting1.refresh_from_db()
        self.assertTrue(self.setting1.is_deleted)

        # Verify setting attributes were marked as deleted
        self.setting_attribute.refresh_from_db()
        self.assertTrue(self.setting_attribute.is_deleted)

        # Verify template used_setting_number was decreased
        self.template.refresh_from_db()
        self.assertEqual(self.template.used_setting_number, 1)

        # Verify priority was updated for other settings
        self.setting2.refresh_from_db()
        self.assertEqual(self.setting2.priority, 1)

    def test_delete_with_transaction_rollback(self):
        """Test deletion with transaction rollback on error"""
        with patch('osf.models.ProjectLimitNumberSetting.save') as mock_save:
            mock_save.side_effect = Exception('Database error')

            request = RequestFactory().delete(self.base_url)
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            with self.assertRaises(Exception):
                self.view.delete(request, setting_id=self.setting1.id)

            # Verify nothing was changed due to rollback
            self.setting1.refresh_from_db()
            self.assertFalse(self.setting1.is_deleted)

            self.setting_attribute.refresh_from_db()
            self.assertFalse(self.setting_attribute.is_deleted)

            self.template.refresh_from_db()
            self.assertEqual(self.template.used_setting_number, 2)

            self.setting2.refresh_from_db()
            self.assertEqual(self.setting2.priority, 2)

    def test_delete_last_priority_setting(self):
        """Test deleting setting with highest priority"""
        request = RequestFactory().delete(f'/project-limit-number/settings/{self.setting2.id}/delete/')
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.delete(request, setting_id=self.setting2.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify first setting's priority wasn't changed
        self.setting1.refresh_from_db()
        self.assertEqual(self.setting1.priority, 1)


class TestProjectLimitNumberSettingCreateView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.template_patcher = patch('admin.project_limit_number.setting.views.render_bad_request_response')
        self.mock_render = self.template_patcher.start()
        self.mock_render.return_value.status_code = HTTPStatus.BAD_REQUEST
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create user
        self.user = AuthUserFactory()

        # Create template with attributes
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template',
            is_availability=True,
            is_deleted=False
        )

        self.list_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='List Attribute',
            setting_type=5,
            attribute_value='value1, value2, value3',
            is_deleted=False
        )

        self.fixed_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Fixed Attribute',
            setting_type=3,
            attribute_value='fixed_value',
            is_deleted=False
        )

        # Create base URL
        self.base_url = '/project-limit-number/settings/create/'

        # Create view class
        self.view = ProjectLimitNumberSettingCreateView()
        self.view.kwargs = {}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.get(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.get(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_get_missing_institution_id_super_admin(self):
        """Test super admin access without institution_id"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The institution id is required.'
        )

    def test_get_invalid_institution_id_format(self):
        """Test with invalid institution_id format"""
        request = self.request_factory.get(f'{self.base_url}?institution_id=invalid')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': 'invalid'}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The institution id is invalid.'
        )

    def test_get_nonexistent_institution(self):
        """Test with non-existent institution"""
        request = self.request_factory.get(f'{self.base_url}?institution_id=-1')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': -1}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The institution not exist.'
        )

    def test_get_invalid_template_id_format(self):
        """Test with invalid template_id format"""
        request = self.request_factory.get(
            f'{self.base_url}?institution_id={self.institution.id}&template_id=invalid'
        )
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id, 'template_id': 'invalid'}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The template id is invalid.'
        )

    def test_get_nonexistent_template(self):
        """Test with non-existent template"""
        request = self.request_factory.get(
            f'{self.base_url}?institution_id={self.institution.id}&template_id=-1'
        )
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id, 'template_id': -1}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.mock_render.assert_called_with(
            request=request,
            error_msgs='The template not exist.'
        )

    def test_get_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.get(f'{self.base_url}?institution_id={self.institution.id}')
        request.user = self.institution_admin
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view = setup_view(self.view, request)

        with self.assertRaises(PermissionDenied):
            self.view.get(request)

    def test_get_with_template_id(self):
        """Test successful GET request with template_id"""
        request = self.request_factory.get(
            f'{self.base_url}?institution_id={self.institution.id}&template_id={self.template.id}'
        )
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id, 'template_id': self.template.id}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        context = response.context_data
        self.assertEqual(context['institution'], self.institution)
        self.assertIsNotNone(context['template_id'])
        self.assertIn('template_list', context)
        self.assertIn('template_attribute_list', context)

        # Verify template attributes are properly formatted
        template_attrs = context['template_attribute_list']
        list_attr = next(attr for attr in template_attrs if attr['setting_type'] in LIST_VALUE_SETTING_TYPE_LIST)
        self.assertIsInstance(list_attr['attribute_value'], list)
        self.assertEqual(len(list_attr['attribute_value']), 3)

    def test_get_without_template_id(self):
        """Test successful GET request without template_id"""
        request = self.request_factory.get(f'{self.base_url}?institution_id={self.institution.id}')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        context = response.context_data
        self.assertEqual(context['institution'], self.institution)
        self.assertIn('template_list', context)
        self.assertIsNone(context['template_id'])

    def test_get_with_no_available_template(self):
        """Test successful GET request in case there are no available template in DB """
        self.template.is_deleted = True
        self.template.save()
        request = self.request_factory.get(f'{self.base_url}?institution_id={self.institution.id}')
        request.user = self.super_admin
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        context = response.context_data
        self.assertEqual(context['institution'], self.institution)
        self.assertIn('template_list', context)
        self.assertEqual(len(context['template_list']), 0)

    def test_get_institution_admin_affiliated_institution(self):
        """Test institution admin accessing affiliated institution"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.get(f'{self.base_url}?institution_id={self.institution.id}')
        request.user = self.institution_admin
        self.view.kwargs = {'institution_id': self.institution.id}
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context_data['institution'], self.institution)


class TestCreateProjectLimitNumberSettingView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template',
            is_availability=True,
            is_deleted=False
        )

        # Create template attributes
        self.fixed_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Fixed Attribute',
            setting_type=3,
            attribute_value='fixed_value',
            is_deleted=False
        )

        self.list_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='List Attribute',
            setting_type=5,
            attribute_value='value1, value2, value3',
            is_deleted=False
        )

        # Create base URL
        self.base_url = '/project-limit-number/settings/create/'

        # Create view class
        self.view = ProjectLimitNumberSettingCreateView()
        self.view.kwargs = {}

        # Create valid request data
        self.valid_data = {
            'institution_id': self.institution.id,
            'template_id': self.template.id,
            'name': 'Test Setting',
            'memo': 'Test Memo',
            'project_limit_number': 5,
            'attribute_list': [
                {
                    'attribute_id': self.fixed_attribute.id,
                    'attribute_value': 'fixed_value'
                },
                {
                    'attribute_id': self.list_attribute.id,
                    'attribute_value': 'value1'
                }
            ]
        }

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        data = self.valid_data.copy()
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        data = self.valid_data.copy()
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        data = self.valid_data.copy()
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        data = self.valid_data.copy()
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)
        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_post_invalid_attribute_list(self):
        """Test with invalid attribute list"""
        data = self.valid_data.copy()
        data['attribute_list'] = []  # Empty attribute list

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'attribute_list is required.'}
        )

    def test_post_invalid_json_body(self):
        """Test with invalid JSON in request body"""
        request = self.request_factory.post(
            self.base_url,
            data='invalid json',
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The request body is invalid.'}
        )

    def test_post_name_having_only_space(self):
        """Test with name having only spaces"""
        data = self.valid_data.copy()
        data['name'] = '   '

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'name is required.'}
        )

    def test_post_project_limit_number_exceeds_maximum(self):
        """Test with project limit number exceeding maximum allowed"""
        data = self.valid_data.copy()
        data['project_limit_number'] = settings.PROJECT_LIMIT_NUMBER + 1

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'project_limit_number is invalid.'}
        )

    def test_post_duplicate_attribute_ids(self):
        """Test with duplicate attribute IDs in attribute_list"""
        data = self.valid_data.copy()
        data['attribute_list'] = [
            {
                'attribute_id': self.fixed_attribute.id,
                'attribute_value': 'value1'
            },
            {
                'attribute_id': self.fixed_attribute.id,
                'attribute_value': 'value2'
            }
        ]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'attribute_id is invalid.'}
        )

    def test_post_nonexistent_institution(self):
        """Test with non-existent institution"""
        data = self.valid_data.copy()
        data['institution_id'] = -1

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The institution not exist.'}
        )

    def test_post_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Forbidden'}
        )

    def test_post_existed_setting_name(self):
        """Test with existed setting name"""
        # Create existing setting
        ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Test Setting',
            priority=1,
            is_deleted=False
        )

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The setting name already exists.'}
        )

    def test_post_nonexistent_template(self):
        """Test with non-existent template"""
        data = self.valid_data.copy()
        data['template_id'] = -1

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The template not exist.'}
        )

    @patch('admin.project_limit_number.utils.validate_file_json')
    def test_post_schema_validation_failure(self, mock_validate):
        """Test schema validation failure"""
        mock_validate.return_value = (False, 'Schema validation error')

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Schema validation error'}
        )

    def test_post_invalid_attribute_count(self):
        """Test with invalid number of attributes"""
        data = self.valid_data.copy()
        data['attribute_list'] = [data['attribute_list'][0]]  # Remove one attribute

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute list is invalid.'}
        )

    def test_post_nonexistent_attribute(self):
        """Test with non-existent attribute"""
        data = self.valid_data.copy()
        data['attribute_list'][0]['attribute_id'] = -1

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute not exist.'}
        )

    def test_post_invalid_fixed_value(self):
        """Test with invalid fixed value attribute"""
        data = self.valid_data.copy()
        data['attribute_list'][0]['attribute_value'] = 'wrong_value'

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute value is invalid.'}
        )

    def test_post_invalid_list_value(self):
        """Test with invalid list value attribute"""
        data = self.valid_data.copy()
        data['attribute_list'][1]['attribute_value'] = 'invalid_value'

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute value is invalid.'}
        )

    def test_post_successful(self):
        """Test successful creation of setting"""
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # Verify setting was created
        setting = ProjectLimitNumberSetting.objects.filter(
            institution_id=self.institution.id,
            name=self.valid_data['name']
        ).first()

        self.assertIsNotNone(setting)
        self.assertEqual(setting.template_id, self.template.id)
        self.assertEqual(setting.memo, self.valid_data['memo'])
        self.assertEqual(setting.project_limit_number, self.valid_data['project_limit_number'])

        # Verify attributes were created
        attributes = ProjectLimitNumberSettingAttribute.objects.filter(setting=setting)
        self.assertEqual(attributes.count(), 2)

        # Verify template used_setting_number increased by 1
        self.template.refresh_from_db()
        self.assertEqual(self.template.used_setting_number, 1)


class TestProjectLimitNumberSettingDetailView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.request_factory = RequestFactory()

        # Create users
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        self.user = AuthUserFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create template and template attributes
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template'
        )

        self.template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Test Attribute',
            setting_type=5,
            attribute_value='value1, value2, value3'
        )

        # Create setting
        self.setting = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Test Setting',
            memo='Test Memo',
            project_limit_number=10,
            priority=1,
            is_deleted=False
        )

        # Create setting attribute
        self.setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting,
            attribute=self.template_attribute,
            attribute_value='value1'
        )

        # Create base URL
        self.base_url = f'/project-limit-number/settings/{self.setting.id}/'

        # Create view class
        self.view = ProjectLimitNumberSettingDetailView()
        self.view.kwargs = {}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.get(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.get(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_get_setting_data(self):
        """Test getting setting data"""
        setting_data = self.view.get_setting_data(self.setting.id)

        self.assertTrue(len(setting_data) > 0)
        first_data = setting_data[0]
        self.assertEqual(first_data['id'], self.setting.id)
        self.assertEqual(first_data['name'], self.setting.name)
        self.assertEqual(first_data['institution_id'], self.institution.id)

    def test_get_nonexistent_setting(self):
        """Test getting non-existent setting"""
        request = self.request_factory.get('/project-limit-number/settings/-1/')
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        with self.assertRaises(Http404):
            self.view.get(request, setting_id=-1)

    def test_get_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution's setting"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.get(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        with self.assertRaises(PermissionDenied):
            self.view.get(request, setting_id=self.setting.id)

    def test_get_setting_with_list_value_type(self):
        """Test getting setting with list value type"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.get(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, 200)

        context = response.context_data
        self.assertIn('setting_attribute_list', context)
        first_attribute = context['setting_attribute_list'][0]
        self.assertIn('attribute_value_select_list', first_attribute)
        self.assertEqual(len(first_attribute['attribute_value_select_list']), 3)

    def test_get_setting_context_data(self):
        """Test context data in get response"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.get(request, setting_id=self.setting.id)
        context = response.context_data

        self.assertIn('template_name', context)
        self.assertIn('setting', context)
        self.assertIn('institution_id', context)
        self.assertEqual(context['setting']['id'], self.setting.id)
        self.assertEqual(context['setting']['name'], self.setting.name)
        self.assertEqual(context['setting']['project_limit_number'], self.setting.project_limit_number)

    def test_get_deleted_setting(self):
        """Test getting deleted setting"""
        self.setting.is_deleted = True
        self.setting.save()

        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        with self.assertRaises(Http404):
            self.view.get(request, setting_id=self.setting.id)


class TestUpdateProjectLimitNumberSettingView(AdminTestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template',
            is_availability=True,
            is_deleted=False
        )

        # Create template attributes
        self.template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Test Attribute',
            setting_type=5,
            attribute_value='value1, value2, value3',
            is_deleted=False
        )

        self.fixed_template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Fixed Attribute',
            setting_type=3,
            attribute_value='fixed_value',
            is_deleted=False
        )

        # Create setting
        self.setting = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Test Setting',
            memo='Original Memo',
            project_limit_number=5,
            priority=1,
            is_deleted=False
        )

        # Create setting attribute
        self.setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting,
            attribute=self.template_attribute,
            attribute_value='value1',
            is_deleted=False
        )

        self.fixed_setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting,
            attribute=self.fixed_template_attribute,
            attribute_value='fixed_value',
            is_deleted=False
        )

        # Create base URL
        self.base_url = f'/project-limit-number/settings/{self.setting.id}/update/'

        # Create view class
        self.view = UpdateProjectLimitNumberSettingView()
        self.view.kwargs = {'setting_id': self.setting.id}

        # Create valid request data
        self.valid_data = {
            'name': 'Updated Setting',
            'memo': 'Updated Memo',
            'project_limit_number': 10,
            'attribute_list': [
                {
                    'id': self.setting_attribute.id,
                    'attribute_value': 'value2'
                },
                {
                    'id': self.fixed_setting_attribute.id,
                    'attribute_value': 'fixed_value'
                }
            ]
        }

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.put(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)
        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.put(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.put(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = self.request_factory.put(self.base_url)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)
        # Assert handle_no_permission
        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_put_invalid_json_body(self):
        """Test with invalid JSON in request body"""
        request = self.request_factory.put(
            self.base_url,
            data='invalid json',
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_put_name_having_only_space(self):
        """Test with name having only spaces in request data"""
        data = self.valid_data.copy()
        data['name'] = '  '

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'name is required.'}
        )

    def test_put_project_limit_number_exceeds_maximum(self):
        """Test with project limit number exceeding maximum allowed"""
        data = self.valid_data.copy()
        data['project_limit_number'] = settings.PROJECT_LIMIT_NUMBER + 1

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'project_limit_number is invalid.'}
        )

    def test_put_duplicate_attribute_ids(self):
        """Test with duplicate attribute IDs in attribute_list"""
        data = self.valid_data.copy()
        data['attribute_list'] = [
            {
                'id': self.setting_attribute.id,
                'attribute_value': 'value1'
            },
            {
                'id': self.setting_attribute.id,
                'attribute_value': 'value2'
            }
        ]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'id is invalid.'}
        )

    def test_put_nonexistent_setting(self):
        """Test updating non-existent setting"""
        self.view.kwargs = {'setting_id': -1}
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=-1)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The setting not exist.'}
        )

    def test_put_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Forbidden'}
        )

    def test_put_duplicate_setting_name(self):
        """Test with duplicate setting name"""
        # Create another setting with the name we want to update to
        ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name=self.valid_data['name'],
            priority=2,
            is_deleted=False
        )

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The setting name already exists.'}
        )

    def test_put_invalid_attribute_list_length(self):
        """Test with invalid attribute list length"""
        data = self.valid_data.copy()
        data['attribute_list'] = []

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'attribute_list is required.'}
        )

    @patch('admin.project_limit_number.utils.validate_file_json')
    def test_put_schema_validation_failure(self, mock_validate):
        """Test schema validation failure"""
        mock_validate.return_value = (False, 'Schema validation error')

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Schema validation error'}
        )

    def test_put_nonexistent_setting_attribute(self):
        """Test with non-existent setting attribute ID"""
        data = self.valid_data.copy()
        data['attribute_list'] = [{
            'id': self.setting_attribute.id,
            'attribute_value': 'value1'
        }, {
            'id': -1,
            'attribute_value': 'value2'
        }]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute not exist.'}
        )

    def test_put_invalid_fixed_value_attribute(self):
        """Test updating fixed value attribute with invalid value"""
        data = self.valid_data.copy()
        data['attribute_list'] = [
            {
                'id': self.fixed_setting_attribute.id,
                'attribute_value': 'wrong_value'  # Trying to change fixed value
            },
            {
                'id': self.setting_attribute.id,
                'attribute_value': 'value2'
            }
        ]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute value is invalid.'}
        )

    def test_put_invalid_list_value_attribute(self):
        """Test updating list value attribute with invalid value"""
        data = self.valid_data.copy()
        data['attribute_list'] = [
            {
                'id': self.setting_attribute.id,
                'attribute_value': 'invalid_value'  # Value not in list
            },
            {
                'id': self.fixed_setting_attribute.id,
                'attribute_value': 'fixed_value'
            }
        ]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute value is invalid.'}
        )

    def test_put_missing_setting_id(self):
        """Test with missing setting_id in kwargs"""
        self.view.kwargs = {}
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'setting_id is required.'}
        )

    def test_put_deleted_setting_attribute(self):
        """Test with deleted setting attribute"""
        # Mark attribute as deleted
        self.setting_attribute.is_deleted = True
        self.setting_attribute.save()

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The attribute list is invalid.'}
        )

    def test_put_successful_update_with_multiple_attributes(self):
        """Test successful update with multiple attributes"""
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify setting was updated
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.name, self.valid_data['name'])
        self.assertEqual(self.setting.memo, self.valid_data['memo'])
        self.assertEqual(self.setting.project_limit_number, self.valid_data['project_limit_number'])

        # Verify list attribute was updated
        self.setting_attribute.refresh_from_db()
        self.assertEqual(
            self.setting_attribute.attribute_value,
            self.valid_data['attribute_list'][0]['attribute_value']
        )

        # Verify fixed attribute remained unchanged
        self.fixed_setting_attribute.refresh_from_db()
        self.assertEqual(
            self.fixed_setting_attribute.attribute_value,
            self.valid_data['attribute_list'][1]['attribute_value']
        )

    def test_put_update_without_changing_name(self):
        """Test update without changing the setting name"""
        data = self.valid_data.copy()
        data['name'] = self.setting.name  # Use existing name

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify setting was updated
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.name, data['name'])

    def test_put_successful_update(self):
        """Test successful update of setting"""
        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify setting was updated
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.name, self.valid_data['name'])
        self.assertEqual(self.setting.memo, self.valid_data['memo'])
        self.assertEqual(self.setting.project_limit_number, self.valid_data['project_limit_number'])

        # Verify attribute was updated
        self.setting_attribute.refresh_from_db()
        self.assertEqual(self.setting_attribute.attribute_value, 'value2')

    def test_put_list_value_attribute_validation(self):
        """Test validation of list value attribute with comma-separated values"""
        # Create template attribute with multiple comma-separated values
        list_template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Multi List Attribute',
            setting_type=6,
            attribute_value='value1, value2, value3, value4',
            is_deleted=False
        )

        list_setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting,
            attribute=list_template_attribute,
            attribute_value='value1',
            is_deleted=False
        )

        data = self.valid_data.copy()
        data['attribute_list'].append({
            'id': list_setting_attribute.id,
            'attribute_value': 'value4'  # Valid value from list
        })

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify attribute was updated
        list_setting_attribute.refresh_from_db()
        self.assertEqual(list_setting_attribute.attribute_value, 'value4')

    def test_put_list_value_attribute_with_spaces(self):
        """Test list value attribute with spaces in values"""
        # Create template attribute with spaces in values
        list_template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Spaced List Attribute',
            setting_type=6,
            attribute_value='value 1, value 2, value 3',
            is_deleted=False
        )

        list_setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting,
            attribute=list_template_attribute,
            attribute_value='value 1',
            is_deleted=False
        )

        data = self.valid_data.copy()
        data['attribute_list'].append({
            'id': list_setting_attribute.id,
            'attribute_value': 'value 2'  # Valid value with space
        })

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify attribute was updated
        list_setting_attribute.refresh_from_db()
        self.assertEqual(list_setting_attribute.attribute_value, 'value 2')

    def test_put_transaction_rollback_on_save_error(self):
        """Test transaction rollback when save operation fails"""
        original_name = self.setting.name
        original_memo = self.setting.memo
        original_attribute_value = self.setting_attribute.attribute_value

        with patch('osf.models.ProjectLimitNumberSetting.save') as mock_save:
            mock_save.side_effect = Exception('Database error')

            request = self.request_factory.put(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            with self.assertRaises(Exception):
                self.view.put(request, setting_id=self.setting.id)

            # Verify no changes were saved due to rollback
            self.setting.refresh_from_db()
            self.setting_attribute.refresh_from_db()

            self.assertEqual(self.setting.name, original_name)
            self.assertEqual(self.setting.memo, original_memo)
            self.assertEqual(self.setting_attribute.attribute_value, original_attribute_value)

    def test_put_transaction_rollback_on_bulk_update_error(self):
        """Test transaction rollback when bulk update operation fails"""
        original_name = self.setting.name
        original_memo = self.setting.memo
        original_attribute_value = self.setting_attribute.attribute_value

        with patch('admin.project_limit_number.setting.views.bulk_update') as mock_bulk_update:
            mock_bulk_update.side_effect = Exception('Bulk update error')

            request = self.request_factory.put(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            with self.assertRaises(Exception):
                self.view.put(request, setting_id=self.setting.id)

            # Verify no changes were saved due to rollback
            self.setting.refresh_from_db()
            self.setting_attribute.refresh_from_db()

            self.assertEqual(self.setting.name, original_name)
            self.assertEqual(self.setting.memo, original_memo)
            self.assertEqual(self.setting_attribute.attribute_value, original_attribute_value)

    def test_put_bulk_update_modified_timestamp(self):
        """Test that modified timestamp is updated during bulk update"""
        old_modified = self.setting_attribute.modified

        # Ensure some time passes
        time.sleep(0.1)

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify modified timestamp was updated
        self.setting_attribute.refresh_from_db()
        self.assertGreater(self.setting_attribute.modified, old_modified)

    def test_put_multiple_attribute_bulk_update(self):
        """Test bulk update of multiple attributes"""
        # Create additional attribute
        additional_template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Additional Attribute',
            setting_type=6,
            attribute_value='val1, val2, val3',
            is_deleted=False
        )

        additional_setting_attribute = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting,
            attribute=additional_template_attribute,
            attribute_value='val1',
            is_deleted=False
        )

        data = self.valid_data.copy()
        data['attribute_list'] = [
            {
                'id': self.setting_attribute.id,
                'attribute_value': 'value2'
            },
            {
                'id': self.fixed_setting_attribute.id,
                'attribute_value': 'fixed_value'
            },
            {
                'id': additional_setting_attribute.id,
                'attribute_value': 'val3'
            }
        ]

        request = self.request_factory.put(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request, setting_id=self.setting.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify both attributes were updated
        self.setting_attribute.refresh_from_db()
        additional_setting_attribute.refresh_from_db()

        self.assertEqual(self.setting_attribute.attribute_value, 'value2')
        self.assertEqual(additional_setting_attribute.attribute_value, 'val3')


class TestUserListView(AdminTestCase):

    def setUp(self):
        """Set up test data for all test methods"""
        self.request_factory = RequestFactory()

        # Create institution
        self.institution = InstitutionFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create institution admin user
        self.institution_admin = AuthUserFactory()
        self.institution_admin.is_staff = True
        self.institution_admin.save()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template',
            is_availability=True,
            is_deleted=False
        )

        # Create template attributes
        self.template_attribute1 = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='displayName',
            setting_type=5,
            attribute_value='displayName1, displayName2, displayName3',
            is_deleted=False
        )

        self.template_attribute2 = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='jaDisplayName',
            setting_type=5,
            attribute_value='jaDisplayName1, jaDisplayName2, jaDisplayName3',
            is_deleted=False
        )

        self.fixed_template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='sn',
            setting_type=3,
            attribute_value='fixed_value',
            is_deleted=False
        )

        # Create users
        self.users = [AuthUserFactory(username=f'user{item}@test.com') for item in range(15)]  # Create 15 users for pagination testing

        self.projects = []
        # Affiliate users with institution and add extended data
        for i, user in enumerate(self.users):
            user.affiliated_institutions.add(self.institution)
            data = {
                'idp_attr': {
                    'fullname': f'displayName{i + 1}',
                    'fullname_ja': f'jaDisplayName{i + 1}',
                    'family_name': 'fixed_value'
                }
            }
            UserExtendedData.objects.create(
                user=user,
                data=data
            )

        # Create project limit number settings with different conditions
        self.setting1 = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Setting 1',
            project_limit_number=5,
            priority=1,
            is_availability=True,
            is_deleted=False
        )

        self.setting2 = ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Setting 2',
            project_limit_number=10,
            priority=2,
            is_availability=True,
            is_deleted=False
        )

        # Create setting attributes for different conditions
        self.setting1_attribute1 = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting1,
            attribute=self.template_attribute1,
            attribute_value='displayName1',
            is_deleted=False
        )

        self.setting1_attribute2 = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting1,
            attribute=self.template_attribute2,
            attribute_value='jaDisplayName1',
            is_deleted=False
        )

        self.setting2_attribute1 = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting2,
            attribute=self.template_attribute1,
            attribute_value='displayName2',
            is_deleted=False
        )

        self.setting2_attribute2 = ProjectLimitNumberSettingAttribute.objects.create(
            setting=self.setting2,
            attribute=self.fixed_template_attribute,
            attribute_value='fixed_value',
            is_deleted=False
        )

        # Create default project limit number
        self.default_limit = ProjectLimitNumberDefault.objects.create(
            institution=self.institution,
            project_limit_number=3
        )

        # Create base URL
        self.base_url = '/project_limit_number/settings/user-list/'

        # Create view class
        self.view = UserListView()
        self.view.kwargs = {}

        # Add valid request data
        self.valid_data = {
            'page': '1',
            'institution_id': self.institution.id,
            'attribute_list': [
                {
                    'attribute_name': 'displayName',
                    'setting_type': 1,
                    'attribute_value': 'displayName1'
                }
            ]
        }

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = self.request_factory.get(self.base_url)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = self.request_factory.get(self.base_url)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_institution_admin(self):
        """Test access with institutional admin"""
        self.institution_admin.affiliated_institutions.add(self.institution)
        request = self.request_factory.get(self.base_url)
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = self.request_factory.get(self.base_url)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

        with self.assertRaises(Exception):
            self.view.handle_no_permission()

    def test_post_invalid_json_body(self):
        """Test with invalid JSON in request body"""
        request = self.request_factory.post(
            self.base_url,
            data='invalid json',
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    @patch('admin.project_limit_number.utils.validate_file_json')
    def test_post_invalid_schema(self, mock_validate):
        """Test with invalid schema"""
        mock_validate.return_value = (False, 'Schema validation error')

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Schema validation error'}
        )

    def test_post_nonexistent_institution(self):
        """Test with non-existent institution"""
        data = self.valid_data.copy()
        data['institution_id'] = -1

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'The institution not exist.'}
        )

    def test_post_institution_admin_wrong_institution(self):
        """Test institution admin accessing wrong institution"""
        other_institution = InstitutionFactory()
        self.institution_admin.affiliated_institutions.add(other_institution)

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.institution_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Forbidden'}
        )

    def test_post_invalid_attribute_name(self):
        """Test with invalid attribute name"""
        data = self.valid_data.copy()
        data['attribute_list'] = [{
            'attribute_name': 'invalid_attribute',
            'setting_type': 1,
            'attribute_value': 'displayName1'
        }]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'attribute_name is invalid.'}
        )

    def test_post_mail_grdm_attribute(self):
        """Test with mail grdm attribute"""
        data = self.valid_data.copy()
        data['attribute_list'] = [{
            'attribute_name': utils.MAIL_GRDM,
            'setting_type': 2,
            'attribute_value': '@test.com'
        }, {
            'attribute_name': utils.MAIL_GRDM,
            'setting_type': 1,
            'attribute_value': 'example1@test.com'
        }]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_multiple_attribute(self):
        """Test with multiple attributes"""
        data = self.valid_data.copy()
        data['attribute_list'] = [{
            'attribute_name': 'displayName',
            'setting_type': 1,
            'attribute_value': 'displayName1'
        }, {
            'attribute_name': 'jaDisplayName',
            'setting_type': 1,
            'attribute_value': 'jaDisplayName1'
        }]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_empty_user_list(self):
        """Test when no users match the criteria"""
        data = self.valid_data.copy()
        data['attribute_list'] = [{
            'attribute_name': 'displayName',
            'setting_type': 1,
            'attribute_value': 'no_match_value'
        }]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            json.loads(response.content),
            {'user_list': [], 'total': 0}
        )

    def test_post_page_none(self):
        """Test requesting page is None"""
        data = self.valid_data.copy()
        data['page'] = None
        data['attribute_list'] = [{
            'attribute_name': 'sn',
            'setting_type': 1,
            'attribute_value': 'fixed_value'
        }]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['user_list']), 10)
        self.assertEqual(response_data['total'], 15)

    def test_post_last_page(self):
        """Test requesting last page"""
        data = self.valid_data.copy()
        data['page'] = 'last'
        data['attribute_list'] = [{
            'attribute_name': 'sn',
            'setting_type': 1,
            'attribute_value': 'fixed_value'
        }]

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['user_list']), 5)
        self.assertEqual(response_data['total'], 15)

    def test_post_page_larger_than_last_page(self):
        """Test requesting page that has larger than the last page number"""
        data = self.valid_data.copy()
        data['page'] = '99999'

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['user_list']), 0)

    def test_post_response_with_settings(self):
        """Test successful response including project limit settings"""
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = json.loads(response.content)
        self.assertIn('user_list', response_data)
        self.assertIn('total', response_data)

        if response_data['user_list']:
            user_data = response_data['user_list'][0]
            self.assertIn('guid', user_data)
            self.assertIn('username', user_data)
            self.assertIn('fullname', user_data)
            self.assertIn('eppn', user_data)

    def test_post_user_meets_first_condition(self):
        """Test when user meets first setting's condition"""
        with patch('admin.project_limit_number.utils.check_logic_condition') as mock_check:
            mock_check.side_effect = [True, False]  # Meets first condition, not second

            request = self.request_factory.post(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            response = self.view.post(request)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            response_data = json.loads(response.content)
            self.assertNotEqual(len(response_data['user_list']), 0)
            for user_data in response_data['user_list']:
                self.assertEqual(user_data.get('project_limit_number'), 5)

    def test_post_user_meets_second_condition(self):
        """Test when user meets second setting's condition"""
        with patch('admin.project_limit_number.utils.check_logic_condition') as mock_check:
            mock_check.side_effect = [False, True]  # Doesn't meet first, meets second

            request = self.request_factory.post(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            response = self.view.post(request)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            response_data = json.loads(response.content)
            self.assertNotEqual(len(response_data['user_list']), 0)
            for user_data in response_data['user_list']:
                self.assertEqual(user_data.get('project_limit_number'), 10)

    def test_post_user_meets_no_conditions(self):
        """Test when user meets no conditions and gets default limit"""
        with patch('admin.project_limit_number.utils.check_logic_condition') as mock_check:
            mock_check.return_value = False  # Meets no conditions

            request = self.request_factory.post(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            response = self.view.post(request)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            response_data = json.loads(response.content)
            self.assertNotEqual(len(response_data['user_list']), 0)
            for user_data in response_data['user_list']:
                self.assertEqual(user_data.get('project_limit_number'), 3)

    def test_post_no_default_limit_configured(self):
        """Test when no default limit is configured"""
        # Delete default limit
        self.default_limit.delete()

        with patch('admin.project_limit_number.utils.check_logic_condition') as mock_check:
            mock_check.return_value = False  # Meets no conditions

            request = self.request_factory.post(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            response = self.view.post(request)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            response_data = json.loads(response.content)
            self.assertNotEqual(len(response_data['user_list']), 0)
            for user_data in response_data['user_list']:
                self.assertEqual(user_data.get('project_limit_number'), utils.NO_LIMIT)

    def test_post_project_count_calculation(self):
        """Test correct calculation of created project numbers"""
        for i, user in enumerate(self.users):
            self.projects.append(ProjectFactory(creator=user, is_deleted=False))
        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        response_data = json.loads(response.content)
        self.assertNotEqual(len(response_data['user_list']), 0)
        for user_data in response_data['user_list']:
            user_projects = len([p for p in self.projects
                                 if p.creator_id == user_data['id']])
            self.assertEqual(user_data['created_project_number'], user_projects)

    def test_post_empty_setting_attributes(self):
        """Test handling of settings with no attributes"""
        # Create setting without attributes
        ProjectLimitNumberSetting.objects.create(
            institution=self.institution,
            template=self.template,
            name='Empty Setting',
            project_limit_number=7,
            priority=2,
            is_availability=True,
            is_deleted=False
        )

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_deleted_setting_attributes(self):
        """Test handling of deleted setting attributes"""
        # Mark attribute as deleted
        self.setting1_attribute1.is_deleted = True
        self.setting1_attribute1.save()

        request = self.request_factory.post(
            self.base_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_multiple_conditions_same_user(self):
        """Test when user meets multiple conditions (should use first match)"""
        with patch('admin.project_limit_number.utils.check_logic_condition') as mock_check:
            mock_check.return_value = True  # Meets all conditions

            request = self.request_factory.post(
                self.base_url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            request.user = self.super_admin
            self.view = setup_view(self.view, request)

            response = self.view.post(request)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            response_data = json.loads(response.content)
            self.assertNotEqual(len(response_data['user_list']), 0)
            for user_data in response_data['user_list']:
                self.assertEqual(user_data.get('project_limit_number'), 5)

    def test_count_users_no_conditions(self):
        """Test counting users without any conditions"""
        count = self.view.count_user_met_logic_condition(
            self.institution.id,
            '',
            '',
            [],
            []
        )
        self.assertEqual(count, 15)  # All users

    def test_count_users_with_logic_condition(self):
        """Test counting users with logic condition"""
        logic_condition = "data -> 'idp_attr' ->> 'fullname' = %s"
        count = self.view.count_user_met_logic_condition(
            self.institution.id,
            logic_condition,
            '',
            ['displayName1'],
            []
        )
        self.assertEqual(count, 1)

    def test_count_users_with_osf_query(self):
        """Test counting users with OSF user query"""
        include_osf_query = 'u.username LIKE %s'
        count = self.view.count_user_met_logic_condition(
            self.institution.id,
            '',
            include_osf_query,
            [],
            ['%@test.com']
        )
        self.assertEqual(count, 15)

    @patch('django.db.connection.cursor')
    def test_count_users_database_error_handling(self, mock_cursor):
        """Test handling of database errors"""
        mock_cursor.return_value.__enter__.side_effect = DatabaseError('Test DB Error')

        with self.assertRaises(DatabaseError):
            self.view.count_user_met_logic_condition(
                self.institution.id,
                '',
                '',
                [],
                []
            )

    def test_get_user_list_first_page(self):
        """Test getting first page of users"""
        user_list = self.view.get_user_list_met_logic_condition(
            self.institution.id,
            1,
            '',
            '',
            [],
            []
        )
        self.assertEqual(len(user_list), 10)  # First page should have 10 users
        for user in user_list:
            self.assertIn('guid', user)
            self.assertIn('username', user)
            self.assertIn('fullname', user)
            self.assertIn('eppn', user)

    def test_get_user_list_second_page(self):
        """Test getting second page of users"""
        user_list = self.view.get_user_list_met_logic_condition(
            self.institution.id,
            2,
            '',
            '',
            [],
            []
        )
        # Second page should have 5 users (total 15 users)
        self.assertEqual(len(user_list), 5)
        for user in user_list:
            self.assertIn('guid', user)
            self.assertIn('username', user)
            self.assertIn('fullname', user)
            self.assertIn('eppn', user)

    def test_get_user_list_with_logic_condition(self):
        """Test getting user list with logic condition"""
        logic_condition = "data -> 'idp_attr' ->> 'fullname' = %s"
        user_list = self.view.get_user_list_met_logic_condition(
            self.institution.id,
            1,
            logic_condition,
            '',
            ['displayName1'],
            []
        )
        self.assertEqual(len(user_list), 1)

    def test_get_user_list_with_osf_query(self):
        """Test getting user list with OSF user query"""
        include_osf_query = f'u.username = %s'
        user_list = self.view.get_user_list_met_logic_condition(
            self.institution.id,
            1,
            '',
            include_osf_query,
            [],
            [self.users[0].username]
        )
        self.assertEqual(len(user_list), 1)

    def test_get_user_list_with_multiple_osf_query(self):
        """Test getting user list with multiple OSF user queries"""
        include_osf_query = f'u.username = %s AND u.username = %s'
        user_list = self.view.get_user_list_met_logic_condition(
            self.institution.id,
            1,
            '',
            include_osf_query,
            [],
            [self.users[0].username, self.users[1].username]
        )
        self.assertEqual(len(user_list), 0)

    def test_get_user_list_with_both_conditions(self):
        """Test getting user list with both logic condition and OSF query"""
        logic_condition = "data -> 'idp_attr' ->> 'fullname' = %s"
        include_osf_query = f'u.username = %s'

        user_list = self.view.get_user_list_met_logic_condition(
            self.institution.id,
            1,
            logic_condition,
            include_osf_query,
            ['displayName1'],
            [self.users[0].username]
        )
        self.assertEqual(len(user_list), 1)
