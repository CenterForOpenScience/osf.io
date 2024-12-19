from http import HTTPStatus
import json
import mock
from unittest.mock import patch
from django.http import Http404
from django.urls import reverse

from admin.base.settings.defaults import ATTRIBUTE_NAME_LIST, SETTING_TYPE
from osf.models import ProjectLimitNumberTemplate
from django.core.exceptions import PermissionDenied
from osf.models.project_limit_number_template_attribute import ProjectLimitNumberTemplateAttribute
from osf_tests.factories import (
    AuthUserFactory,
    ProjectLimitNumberTemplateFactory
)
from django.test import RequestFactory
from admin.project_limit_number.template import views
from django.contrib.auth.models import AnonymousUser
from admin_tests.utilities import setup_user_view, setup_view
from tests.base import AdminTestCase


class TestProjectLimitNumberTemplateListView(AdminTestCase):

    def setUp(self):
        """Set up test data for all test methods"""
        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create base URL
        self.request = reverse('project_limit_number:templates:list-template')

        # Create template
        self.template = ProjectLimitNumberTemplateFactory(
            template_name='Template 1',
            is_availability=True,
            used_setting_number=0,
            is_deleted=False
        )

        # Create attribute
        ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name='Template attribute 1',
            setting_type=3,
            is_deleted=False
        )

        # Create view class
        self.view = views.ProjectLimitNumberTemplateListView()
        self.view.kwargs = {}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = RequestFactory().get(self.request)
        request.user = AnonymousUser()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertFalse(self.view.raise_exception)

    def test_permission_user(self):
        """Test access with user"""
        request = RequestFactory().get(self.request)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = RequestFactory().get(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    @mock.patch('django.contrib.postgres.aggregates.StringAgg')
    def test_get_queryset(self, mock_stringagg, mock_filter):
        mock_stringagg.return_value = 'eduPersonEntitlement, isMemberOf'
        mock_queryset = mock.MagicMock()
        mock_queryset.annotate.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset

        mock_queryset.values.return_value = [{
            'id': 1,
            'template_name': 'Template 1',
            'is_availability': True,
            'used_setting_number': 5,
            'created': '2024-01-01',
            'modified': '2024-01-02',
            'attribute_names': 'eduPersonEntitlement, isMemberOf',
        }]

        mock_filter.return_value = mock_queryset
        queryset = ProjectLimitNumberTemplate.objects.filter(is_deleted=False, attributes__is_deleted=False) \
            .annotate(
            attribute_names=mock_stringagg(
                'attributes__attribute_name',
                delimiter=', '
            )
        ).order_by('-id').values(
            'id', 'template_name', 'is_availability',
            'used_setting_number', 'created', 'modified', 'attribute_names'
        )

        self.assertEqual(queryset[0]['id'], 1)
        self.assertEqual(queryset[0]['template_name'], 'Template 1')
        self.assertEqual(queryset[0]['attribute_names'], 'eduPersonEntitlement, isMemberOf')
        self.assertEqual(queryset[0]['used_setting_number'], 5)
        mock_filter.assert_called_once_with(is_deleted=False, attributes__is_deleted=False)
        mock_stringagg.assert_called_once_with('attributes__attribute_name', delimiter=', ')
        mock_queryset.values.assert_called_once_with(
            'id', 'template_name', 'is_availability',
            'used_setting_number', 'created', 'modified', 'attribute_names'
        )
        mock_queryset.order_by.assert_called_once_with('-id')

    def test_get_context_data(self):
        """Test context data for super admin"""
        request = RequestFactory().get(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        self.view.object_list = self.view.get_queryset()
        context = self.view.get_context_data()

        self.assertIn('project_limit_number_template_list', context)
        self.assertIn('page', context)

    def test_get_context_page_size_invalid(self):
        self.view.kwargs = {'template_id': 1}
        self.view.request = mock.Mock()
        self.view.request.GET = {'page_size': '20'}
        with self.assertRaises(views.BadRequestException):
            context = self.view.get_context_data(**self.view.kwargs)
            self.assertEqual(context['error_message'], 'The page size is invalid.')

    def test_get_successful(self):
        """Test successful GET request"""
        request = RequestFactory().get(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_get_bad_request(self):
        """Test GET bad request"""
        request = RequestFactory().get(f'{self.request}?page_size=1000')
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        with mock.patch('admin.project_limit_number.template.views.render_bad_request_response') as mock_render_bad_request:
            mock_render_bad_request.return_value.status_code = HTTPStatus.BAD_REQUEST
            response = self.view.get(request)
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_exception(self):
        """Test GET exception"""
        request = RequestFactory().get(f'{self.request}?page_size=invalid')
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        with self.assertRaises(Exception):
            self.view.get(request)


class TestProjectLimitNumberTemplatesViewCreate(AdminTestCase):

    def setUp(self):
        super(TestProjectLimitNumberTemplatesViewCreate, self).setUp()
        self.project_limit_number = ProjectLimitNumberTemplateFactory()
        self.user = AuthUserFactory()
        self.view = views.ProjectLimitNumberTemplatesViewCreate()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        self.request = '/project_limit_number/templates/create/'

    def test_permission_unauthenticated(self):
        self.request = RequestFactory().get(self.request)
        view = setup_user_view(views.ProjectLimitNumberTemplatesViewCreate(), self.request, user=AnonymousUser())
        permission_result = view.test_func()
        self.assertFalse(permission_result)
        self.assertFalse(view.raise_exception)

        # Assert handle_no_permission
        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_permission_unauthenticated_post(self):
        request = RequestFactory().post(self.request)
        request.user = AnonymousUser()
        view = setup_view(self.view, request)
        permission_result = view.test_func()
        self.assertFalse(permission_result)
        self.assertFalse(view.raise_exception)

        # Assert handle_no_permission
        response = self.view.handle_no_permission()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content),
            {'error_message': 'Authentication credentials were not provided.'}
        )

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = RequestFactory().get(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        """Test access with user"""
        request = RequestFactory().get(self.request)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)
        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

        # Assert handle_no_permission
        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_get_context_data(self):
        context = self.view.get_context_data()
        self.assertIn('attribute_name_list', context)
        self.assertEqual(context['attribute_name_list'], ATTRIBUTE_NAME_LIST)
        self.assertIn('setting_type_list', context)
        self.assertEqual(context['setting_type_list'], SETTING_TYPE)

    @mock.patch('osf.models.ProjectLimitNumberTemplateAttribute.save')
    @mock.patch('osf.models.ProjectLimitNumberTemplateAttribute.objects.bulk_create')
    def test_post_valid_data(self, mock_bulk_create, mock_save):
        mock_save.return_value = None
        mock_bulk_create.return_value = [mock.MagicMock()]

        valid_data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 1,
                    'attribute_value': 'os'
                },
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[1],
                    'setting_type': 3,
                    'attribute_value': 'o'
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/',
                                        json.dumps(valid_data),
                                        content_type='application/json')
        response = self.view.post(request)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_post_template_name_only_spaces(self):
        invalid_data = {
            'template_name': '   ',
            'attribute_list': [
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 1,
                    'attribute_value': 'os'
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/',
                                        json.dumps(invalid_data),
                                        content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'template_name is required.')

    def test_post_invalid_attribute_name(self):
        invalid_data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': 'InvalidName',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/', json.dumps(invalid_data), content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'attribute_name is invalid.')

    def test_post_missing_attribute_value(self):
        invalid_data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': 'os',
                    'setting_type': 3,
                    'attribute_value': ''
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/', json.dumps(invalid_data), content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'attribute_value is required.')

    def test_post_invalid_setting_type(self):
        invalid_data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': 'os',
                    'setting_type': 10,
                    'attribute_value': 'attribute_value'
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/', json.dumps(invalid_data), content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'setting_type is invalid.')

    def test_post_invalid_attribute_value_list(self):
        invalid_data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 5,
                    'attribute_value': ','
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/', json.dumps(invalid_data), content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'attribute_value is invalid.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_post_existing_template_name(self, mock_filter):
        mock_filter.return_value.exists.return_value = True
        invalid_data = {
            'template_name': 'Existing Template',
            'attribute_list': [
                {
                    'attribute_name': 'givenName',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().post('/project_limit_number/templates/create/', json.dumps(invalid_data), content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The template name already exists.')

    def test_post_invalid_json(self):
        request = RequestFactory().post('/project_limit_number/templates/create/', '{"template_name": "New Template"', content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The request body is invalid.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.save')
    def test_post_exception(self, mock_save):
        mock_save.side_effect = Exception('Internal server error')
        valid_data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 1,
                    'attribute_value': 'os'
                },
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[1],
                    'setting_type': 2,
                    'attribute_value': 'o'
                }
            ]
        }
        request = RequestFactory().post('/project_limit_number/templates/create/', json.dumps(valid_data), content_type='application/json')
        response = self.view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Internal server error')


class TestProjectLimitNumberTemplatesViewUpdate(AdminTestCase):

    def setUp(self):
        self.project_limit_number = ProjectLimitNumberTemplateFactory()
        self.user = AuthUserFactory()
        self.view = views.ProjectLimitNumberTemplatesViewUpdate()
        self.request = '/project-limit-number/templates/update/'

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

    def test_permission_unauthenticated(self):
        self.request = RequestFactory().get(self.request)
        view = setup_user_view(views.ProjectLimitNumberTemplatesViewUpdate(), self.request, user=AnonymousUser())
        permission_result = view.test_func()
        self.assertEqual(permission_result, False)
        self.assertEqual(view.raise_exception, False)

    def test_permission_user(self):
        """Test access with user"""
        request = RequestFactory().delete(self.request)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)
        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = RequestFactory().get(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_get_context_data(self, mock_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.order_by.return_value.all.return_value = [
            {
                'id': 1,
                'template_name': 'Test Template',
                'used_setting_number': 0,
                'attributes__id': 1,
                'attributes__attribute_name': 'Color',
                'attributes__setting_type': 1,
                'attributes__attribute_value': 'attribute_value'
            }
        ]
        mock_filter.return_value = mock_queryset
        self.view.kwargs = {'template_id': 1}
        context = self.view.get_context_data(**self.view.kwargs)
        self.assertEqual(context['template_name'], 'Test Template')

    @patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_get_context_data_template_not_found(self, mock_filter):
        mock_filter.return_value = ProjectLimitNumberTemplate.objects.none()
        self.view.kwargs = {'template_id': -1}
        with self.assertRaises(Http404):
            self.view.get_context_data()

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_get_context_data_template_is_used(self, mock_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.order_by.return_value.all.return_value = [
            {
                'id': 1,
                'template_name': 'Test Template',
                'used_setting_number': 1,
                'attributes__id': 1,
                'attributes__attribute_name': 'Color',
                'attributes__setting_type': 1,
                'attributes__attribute_value': 'attribute_value'
            }
        ]
        mock_filter.return_value = mock_queryset
        self.view.kwargs = {'template_id': 1}
        with self.assertRaises(views.BadRequestException):
            context = self.view.get_context_data(**self.view.kwargs)
            self.assertEqual(context['error_message'], 'Test Template is being used.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_get_successful(self, mock_filter):
        """Test successful GET request"""
        mock_queryset = mock.MagicMock()
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.order_by.return_value.all.return_value = [
            {
                'id': 1,
                'template_name': 'Test Template',
                'used_setting_number': 0,
                'attributes__id': 1,
                'attributes__attribute_name': 'Color',
                'attributes__setting_type': 1,
                'attributes__attribute_value': 'attribute_value'
            }
        ]
        mock_filter.return_value = mock_queryset
        request = RequestFactory().get(self.request)
        self.view.kwargs = {'template_id': 1}
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.get(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_get_bad_request(self, mock_filter):
        """Test successful GET request"""
        mock_queryset = mock.MagicMock()
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.order_by.return_value.all.return_value = [
            {
                'id': 1,
                'template_name': 'Test Template',
                'used_setting_number': 1,
                'attributes__id': 1,
                'attributes__attribute_name': 'Color',
                'attributes__setting_type': 1,
                'attributes__attribute_value': 'attribute_value'
            }
        ]
        mock_filter.return_value = mock_queryset
        request = RequestFactory().get(self.request)
        self.view.kwargs = {'template_id': 1}
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        with mock.patch('admin.project_limit_number.template.views.render_bad_request_response') as mock_render_bad_request:
            mock_render_bad_request.return_value.status_code = HTTPStatus.BAD_REQUEST
            response = self.view.get(request)
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_get_exception(self, mock_filter):
        """Test successful GET request"""
        mock_filter.return_value = Exception('Exception')
        request = RequestFactory().get(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)
        with self.assertRaises(Exception):
            self.view.get(request)


class TestProjectLimitNumberTemplatesSettingSaveAvailabilityView(AdminTestCase):

    def setUp(self):
        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create template
        self.template1 = ProjectLimitNumberTemplate.objects.create(
            id=1,
            template_name='Test Template 1',
            is_availability=True,
            is_deleted=False
        )

        self.template2 = ProjectLimitNumberTemplate.objects.create(
            id=2,
            template_name='Test Template 2',
            is_availability=True,
            is_deleted=False
        )

        # Create base URL
        self.request = '/project-limit-number/templates/save-availability/'

        # Create view class
        self.view = views.ProjectLimitNumberTemplatesSettingSaveAvailabilityView()
        self.view.kwargs = {}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = RequestFactory().put(self.request)
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

    def test_permission_user(self):
        """Test access with user"""
        request = RequestFactory().put(self.request)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)

        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)

        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = RequestFactory().put(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_put_successful_update(self):
        """Test successful update of settings"""
        valid_data = {
            'data': [
                {
                    'id': 1,
                    'is_availability': True
                },
                {
                    'id': 2,
                    'is_availability': False
                }
            ]
        }
        request = RequestFactory().put(
            self.request,
            data=json.dumps(valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify updates
        self.template1.refresh_from_db()
        self.template2.refresh_from_db()

        self.assertTrue(self.template1.is_availability)
        self.assertFalse(self.template2.is_availability)

    def test_put_data_id_is_invalid(self):
        data = {
            'data': [
                {
                    'id': 1,
                    'is_availability': True
                },
                {
                    'id': 1,
                    'is_availability': False
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'id is invalid.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_template_not_exist(self, mock_filter):
        mock_filter.return_value = [
            mock.MagicMock(
                id=1,
                template_name='Template 1',
                is_deleted=False,
                used_setting_number=0,
                created='2024-01-01',
                modified='2024-01-01',
                is_availability=True
            )
        ]

        data = {
            'data': [
                {
                    'id': 1,
                    'is_availability': True
                },
                {
                    'id': 2,
                    'is_availability': False
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The template not exist.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_template_is_used(self, mock_filter):
        mock_filter.return_value = [
            mock.MagicMock(
                id=1,
                template_name='Template 1',
                is_deleted=False,
                used_setting_number=1,
                created='2024-01-01',
                modified='2024-01-01',
                is_availability=True
            )
        ]

        data = {
            'data': [
                {
                    'id': 1,
                    'is_availability': True
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Template 1 is being used.')

    def test_put_invalid_json(self):
        request = RequestFactory().put(self.request,
                                       "'data': [{'id': 1, 'is_availability': True}]",
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The request body is invalid.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_request_invalid(self, mock_filter):
        mock_filter.return_value = [
            mock.MagicMock(
                id=1,
                template_name='Template 1',
                is_deleted=False,
                used_setting_number=1,
                created='2024-01-01',
                modified='2024-01-01',
                is_availability=True
            )
        ]

        data = {
            'data': [
                {
                    'id': 1,
                    'is_availability': 'True'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'is_availability is invalid.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_internal_server_error(self, mock_filter):
        mock_filter.return_value = Exception('Internal server error')

        data = {
            'data': [
                {
                    'id': 1,
                    'is_availability': True
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Internal server error')


class TestUpdateProjectLimitNumberTemplatesSettingView(AdminTestCase):

    def setUp(self):
        super(TestUpdateProjectLimitNumberTemplatesSettingView, self).setUp()
        self.project_limit_number = ProjectLimitNumberTemplateFactory()
        self.user = AuthUserFactory()

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

        # Create template
        self.template = ProjectLimitNumberTemplate.objects.create(
            template_name='Test Template 1',
            is_availability=True,
            is_deleted=False
        )

        # Create template attribute
        self.template_attribute1 = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name=ATTRIBUTE_NAME_LIST[0],
            setting_type=3,
            attribute_value='attribute_value',
            is_deleted=False
        )

        self.template_attribute2 = ProjectLimitNumberTemplateAttribute.objects.create(
            template=self.template,
            attribute_name=ATTRIBUTE_NAME_LIST[0],
            setting_type=3,
            attribute_value='attribute_value',
            is_deleted=False
        )

        self.request = RequestFactory().put(f'/project_limit_number/templates/{self.template.id}/update/')
        self.request.method = 'PUT'
        self.view = views.UpdateProjectLimitNumberTemplatesSettingView()
        self.view.kwargs = {}

    def test_permission_unauthenticated(self):
        """Test access with unauthenticated user"""
        request = RequestFactory().put(self.request)
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

    def test_permission_user(self):
        """Test access with user"""
        request = RequestFactory().put(self.request)
        request.user = AuthUserFactory()
        self.view = setup_view(self.view, request)

        # Assert test_func
        self.assertFalse(self.view.test_func())
        self.assertTrue(self.view.raise_exception)
        # Assert handle_no_permission
        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    def test_permission_super_admin(self):
        """Test access with super admin"""
        request = RequestFactory().put(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_put_invalid_json(self):
        request = RequestFactory().put(self.request,
                                       "'data': [{'id': 1, 'is_availability': True}]",
                                       content_type='application/json')
        response = self.view.put(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The request body is invalid.')

    def test_put_data_request_invalid(self):
        data = {
            'template_name': '',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'template_name is required.')

    def test_put_template_name_only_spaces(self):
        data = {
            'template_name': '   ',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'template_name is required.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_internal_server_error(self, mock_filter):
        mock_filter.return_value = Exception('Internal server error')
        data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': 'InvalidName',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Internal server error')

    def test_put_deleted_template(self):
        self.template.is_deleted = True
        self.template.save()

        data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'attribute_name': 'os',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The template not exist.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_id_is_invalid(self, mock_filter):
        mock_filter.return_value = [
            mock.MagicMock(
                id=1,
                template_name='Template 1',
                is_deleted=False,
                used_setting_number=0,
                created='2024-01-01',
                modified='2024-01-01',
                is_availability=True
            )
        ]

        data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': 'os',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                },
                {
                    'id': 1,
                    'attribute_name': 'os',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'id is invalid.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_template_is_used(self, mock_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template 1',
            is_deleted=False,
            used_setting_number=1,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.all.return_value = [
            {
                'id': 1,
                'attribute_name': 'os',
                'setting_type': 1,
                'attribute_value': 'attribute_value',
            }
        ]
        mock_filter.return_value = mock_queryset

        data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': 'os',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }
        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Template 1 is being used.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_template_name_already_exists(self, mock_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template 1',
            is_deleted=False,
            used_setting_number=0,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.all.return_value = [
            {
                'id': 1,
                'attribute_name': 'os',
                'setting_type': 1,
                'attribute_value': 'attribute_value',
            }
        ]
        mock_filter.return_value = mock_queryset

        data = {
            'template_name': 'New Template',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': 'os',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The template name already exists.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_put_data_attribute_not_exists(self, mock_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template',
            is_deleted=False,
            used_setting_number=0,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.all.return_value = [
            {
                'id': 1,
                'attribute_name': 'os',
                'setting_type': 1,
                'attribute_value': 'attribute_value',
            }
        ]
        mock_filter.return_value = mock_queryset

        data = {
            'template_name': 'Template',
            'attribute_list': [
                {
                    'id': 2,
                    'attribute_name': 'os',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'The attribute not exist.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    @mock.patch('osf.models.ProjectLimitNumberTemplateAttribute.objects.filter')
    def test_put_data_attribute_value_is_required(self, mock_attribute_filter, mock_template_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template',
            is_deleted=False,
            used_setting_number=0,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_template_filter.return_value = mock_queryset

        mock_queryset_attribute = mock.MagicMock()
        mock_queryset_attribute.values.return_value.all.return_value = [
            {
                'id': 1,
                'attribute_name': 'os',
                'setting_type': 1,
                'attribute_value': 'attribute_value',
            }
        ]
        mock_attribute_filter.return_value = mock_queryset_attribute

        data = {
            'template_name': 'Template',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': 'os',
                    'setting_type': 3,
                    'attribute_value': ''
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'attribute_value is required.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    @mock.patch('osf.models.ProjectLimitNumberTemplateAttribute.objects.filter')
    def test_put_data_attribute_name_is_invalid(self, mock_attribute_filter, mock_template_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template',
            is_deleted=False,
            used_setting_number=0,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_template_filter.return_value = mock_queryset

        mock_queryset_attribute = mock.MagicMock()
        mock_queryset_attribute.values.return_value.all.return_value = [
            {
                'id': 1,
                'attribute_name': 'os',
                'setting_type': 1,
                'attribute_value': 'attribute_value',
            }
        ]
        mock_attribute_filter.return_value = mock_queryset_attribute

        data = {
            'template_name': 'Template',
            'attribute_list': [
                {
                    'id': 1,
                    'attribute_name': 'invalid',
                    'setting_type': 1,
                    'attribute_value': 'attribute_value'
                }
            ]
        }

        request = RequestFactory().put(self.request,
                                       json.dumps(data),
                                       content_type='application/json')
        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'attribute_name is invalid.')

    def test_put_attribute_value_list_is_invalid(self):
        """Test put attribute value list is invalid"""
        data = {
            'template_name': 'Template',
            'attribute_list': [
                {
                    'id': self.template_attribute1.id,
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 5,
                    'attribute_value': ','
                }
            ]
        }

        request = RequestFactory().put(
            self.request,
            json.dumps(data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request, template_id=self.template.id)

        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'attribute_value is invalid.')

    def test_put_successful_update_with_multiple_attributes(self):
        """Test successful update with multiple attributes"""
        valid_data = {
            'template_name': 'Template',
            'attribute_list': [
                {
                    'id': self.template_attribute1.id,
                    'attribute_name': ATTRIBUTE_NAME_LIST[0],
                    'setting_type': 3,
                    'attribute_value': 'new_attribute_value'
                },
                {
                    'attribute_name': ATTRIBUTE_NAME_LIST[1],
                    'setting_type': 1
                }
            ]
        }

        request = RequestFactory().put(
            self.request,
            json.dumps(valid_data),
            content_type='application/json'
        )
        request.user = self.super_admin
        self.view = setup_view(self.view, request, template_id=self.template.id)

        response = self.view.put(request, template_id=self.template.id)
        self.assertEqual(json.loads(response.content), {})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify template was updated
        self.template.refresh_from_db()
        self.assertEqual(self.template.template_name, 'Template')
        self.assertEqual(self.template.used_setting_number, 0)
        self.assertEqual(self.template.is_availability, True)
        self.assertEqual(self.template.is_deleted, False)

        # Verify list attribute was updated
        self.template_attribute1.refresh_from_db()
        self.assertEqual(self.template.attributes.count(), 3)
        self.assertEqual(self.template_attribute1.attribute_name, ATTRIBUTE_NAME_LIST[0])
        self.assertEqual(self.template_attribute1.setting_type, 3)
        self.assertEqual(self.template_attribute1.attribute_value, 'new_attribute_value')

        # Verify new attribute was created
        new_attribute = self.template.attributes.get(attribute_name=ATTRIBUTE_NAME_LIST[1])
        self.assertEqual(new_attribute.setting_type, 1)
        self.assertEqual(new_attribute.attribute_value, None)


class TestDeleteProjectLimitNumberTemplatesSettingView(AdminTestCase):

    def setUp(self):
        super(TestDeleteProjectLimitNumberTemplatesSettingView, self).setUp()
        self.project_limit_number = ProjectLimitNumberTemplateFactory()
        self.user = AuthUserFactory()
        self.request = RequestFactory().delete('/project_limit_number/templates/delete/1/')
        self.request.method = 'Delete'
        self.view = views.DeleteProjectLimitNumberTemplatesSettingView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        # Create super admin user
        self.super_admin = AuthUserFactory()
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()

    def test_permission_unauthenticated(self):
        request = RequestFactory().delete(self.request)
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
        request = RequestFactory().delete(self.request)
        request.user = self.super_admin
        self.view = setup_view(self.view, request)

        self.assertTrue(self.view.test_func())

    def test_permission_user(self):
        view = setup_user_view(views.DeleteProjectLimitNumberTemplatesSettingView(), self.request, user=self.user)
        permission_result = view.test_func()
        self.assertEqual(permission_result, False)
        self.assertEqual(view.raise_exception, True)

        # Assert handle_no_permission
        with self.assertRaises(PermissionDenied):
            self.view.handle_no_permission()

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_delete_data_template_not_found(self, mock_template_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = None
        mock_template_filter.return_value = mock_queryset

        request = RequestFactory().delete('/project_limit_number/templates/delete/1/',
                                          json.dumps("{'template_id': 1}"),
                                          content_type='application/json')
        response = self.view.delete(request)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Template not found')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_delete_data_template_is_being_used(self, mock_template_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template',
            is_deleted=False,
            used_setting_number=1,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_template_filter.return_value = mock_queryset

        request = RequestFactory().delete('/project_limit_number/templates/delete/1/',
                                          json.dumps("{'template_id': 1}"),
                                          content_type='application/json')
        response = self.view.delete(request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Template is being used.')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    def test_delete_data_internal_server_error(self, mock_filter):
        mock_filter.return_value = Exception('Internal server error')
        request = RequestFactory().delete('/project_limit_number/templates/delete/1/',
                                          json.dumps("{'template_id': 1}"),
                                          content_type='application/json')
        response = self.view.delete(request)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error_message'], 'Internal server error')

    @mock.patch('osf.models.ProjectLimitNumberTemplate.objects.filter')
    @mock.patch('osf.models.ProjectLimitNumberTemplateAttribute.objects.filter')
    def test_delete_data_valid(self, mock_attribute_filter, mock_template_filter):
        mock_queryset = mock.MagicMock()
        mock_queryset.first.return_value = mock.MagicMock(
            id=1,
            template_name='Template',
            is_deleted=False,
            used_setting_number=0,
            created='2024-01-01',
            modified='2024-01-01',
            is_availability=True
        )
        mock_queryset.return_value.update = mock_queryset
        mock_template_filter.return_value = mock_queryset

        mock_queryset_attribute = mock.MagicMock()
        mock_queryset_attribute.return_value.update = [
            {
                'id': 1,
                'attribute_name': ATTRIBUTE_NAME_LIST[0],
                'setting_type': 1,
                'attribute_value': 'attribute_value',
                'is_deleted': True
            }
        ]
        mock_attribute_filter.return_value = mock_queryset_attribute
        request = RequestFactory().delete('/project_limit_number/templates/delete/1/',
                                          json.dumps("{'template_id': 1}"),
                                          content_type='application/json')
        response = self.view.delete(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
