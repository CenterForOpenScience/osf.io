from __future__ import unicode_literals

import logging

from django.utils import timezone
import json
from django.http import Http404, JsonResponse

from admin.base import settings
from admin.base.utils import render_bad_request_response
from admin.base.views import GuidFormView
from django.views.generic import UpdateView, ListView, DeleteView
from admin.rdm.utils import RdmPermissionMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from osf.models import ProjectLimitNumberTemplate, ProjectLimitNumberTemplateAttribute
from admin.base.settings import ATTRIBUTE_NAME_LIST, SETTING_TYPE
from django.db import transaction
from django_bulk_update.helper import bulk_update
from http import HTTPStatus
from django.db.models import TextField, Value
from admin.project_limit_number import utils

from django.db.models import Aggregate

logger = logging.getLogger(__name__)
SETTING_TYPE_FREE_VALUE_LIST = [item[0] for item in settings.SETTING_TYPE if item[1].startswith('free_value')]
SETTING_TYPE_REQUIRED_VALUE_LIST = [3, 4, 5, 6]
SETTING_TYPE_LIST_VALUE_LIST = [item[0] for item in settings.SETTING_TYPE if item[1].startswith('list_value')]
PAGE_SIZE_LIST = [10, 25, 50]


class BadRequestException(Exception):
    def __init__(self, message):
        # Initialize with a custom message
        self.message = message
        super().__init__(self.message)


class CustomStringAgg(Aggregate):
    function = 'STRING_AGG'
    template = '%(function)s(%(expressions)s %(ordering)s)'
    output_field = TextField()

    def __init__(self, expression, delimiter, **extra):
        delimiter_expr = Value(str(delimiter))
        super().__init__(expression, delimiter_expr, **extra)


class ProjectLimitNumberTemplateListView(RdmPermissionMixin, UserPassesTestMixin, ListView):
    """ Project Limit Number Template List page """
    template_name = 'project_limit_number_templates/list.html'
    object_type = 'project_limit_number_templates'
    paginate_by = 10
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin

    def get_queryset(self):
        return ProjectLimitNumberTemplate.objects.filter(is_deleted=False, attributes__is_deleted=False) \
            .annotate(
                attribute_names=CustomStringAgg(
                    'attributes__attribute_name',
                    delimiter=', ',
                    ordering='ORDER BY osf_project_limit_number_template_attribute.id ASC'
                )).values(
                'id', 'template_name', 'is_availability',
                'used_setting_number', 'created', 'modified', 'attribute_names').order_by('-id')

    def get_context_data(self, **kwargs):
        query_set = self.get_queryset()
        self.paginate_by = self.request.GET.get('page_size')
        # Validate page_size
        if self.paginate_by and len(self.paginate_by.strip()) > 0:
            # Try casting page_size to integer
            try:
                self.paginate_by = int(self.paginate_by)
                if self.paginate_by not in PAGE_SIZE_LIST:
                    # If page size is not in PAGE_SIZE_LIST then return HTTP 400
                    raise BadRequestException('The page size is invalid.')
            except ValueError:
                # If page size is not a number then return HTTP 400
                raise BadRequestException('The page size is invalid.')
        else:
            self.paginate_by = 10
        page_size = self.get_paginate_by(query_set)
        _, page, query_set, _ = self.paginate_queryset(query_set, page_size)
        data = []
        for query_data in query_set:
            data.append(
                {
                    'id': query_data.get('id'),
                    'template_name': query_data.get('template_name'),
                    'attribute_names': query_data.get('attribute_names'),
                    'is_availability': query_data.get('is_availability'),
                    'used_setting_number': query_data.get('used_setting_number'),
                    'created': query_data.get('created'),
                    'modified': query_data.get('modified')
                }
            )
        kwargs.setdefault('project_limit_number_template_list', data)
        kwargs.setdefault('page', page)
        return super(ProjectLimitNumberTemplateListView, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except BadRequestException as e:
            return render_bad_request_response(request=request, error_msgs=e.args[0])


class ProjectLimitNumberTemplatesViewCreate(RdmPermissionMixin, UserPassesTestMixin, GuidFormView):
    """ Project Limit Number Template Create page """
    template_name = 'project_limit_number_templates/create.html'
    object_type = 'project_limit_number_templates'
    raise_exception = True

    def test_func(self):
        if not self.is_authenticated:
            self.raise_exception = False
            return False
        return self.is_super_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception and self.request.method == 'POST':
            # If request is POST and user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(ProjectLimitNumberTemplatesViewCreate, self).handle_no_permission()

    def get_context_data(self, **kwargs):
        # Return data
        return {
            'attribute_name_list': ATTRIBUTE_NAME_LIST,
            'setting_type_list': SETTING_TYPE,
        }

    def validate_data(self, request_data):
        # Validate request data
        is_request_valid, message = utils.validate_file_json(request_data, 'create-template-project-limit-number-setting-schema.json')
        if not is_request_valid:
            return JsonResponse({'error_message': message}, status=HTTPStatus.BAD_REQUEST)

        # Validate template_name
        template_name = request_data.get('template_name')
        if template_name is None or not template_name.strip():
            return JsonResponse({'error_message': 'template_name is required.'}, status=HTTPStatus.BAD_REQUEST)

        # Validate attribute_value
        attribute_list = request_data.get('attribute_list')
        for attribute in attribute_list:
            attribute_value = attribute.get('attribute_value') or ''
            if attribute.get('setting_type') in SETTING_TYPE_REQUIRED_VALUE_LIST and not attribute_value.strip():
                return JsonResponse({'error_message': 'attribute_value is required.'}, status=HTTPStatus.BAD_REQUEST)
            if attribute.get('attribute_name') not in ATTRIBUTE_NAME_LIST:
                return JsonResponse({'error_message': 'attribute_name is invalid.'}, status=HTTPStatus.BAD_REQUEST)
            if attribute.get('setting_type') in SETTING_TYPE_LIST_VALUE_LIST:
                attribute_value_list = [item.strip() for item in attribute_value.split(',')]
                if '' in attribute_value_list:
                    return JsonResponse({'error_message': 'attribute_value is invalid.'}, status=HTTPStatus.BAD_REQUEST)

        # Trim template name before query
        template_name = template_name.strip()
        # Check template name is exist
        is_exist = ProjectLimitNumberTemplate.objects.filter(
            template_name=template_name,
            is_deleted=False
        ).exists()
        if is_exist:
            return JsonResponse({'error_message': 'The template name already exists.'}, status=HTTPStatus.BAD_REQUEST)
        return None

    def post(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            template_name = request_body.get('template_name')
            result_validate = self.validate_data(request_body)
            if result_validate is not None:
                return result_validate
            # Trim template name
            template_name = template_name.strip()
            # Insert data into osf_project_limit_number_template table
            with transaction.atomic():
                # Insert new template
                template = ProjectLimitNumberTemplate(
                    template_name=template_name
                )
                template.save()

                attribute_list = request_body.get('attribute_list')
                new_attribute_list = []
                for attribute in attribute_list:
                    setting_type = attribute.get('setting_type')
                    if setting_type in SETTING_TYPE_FREE_VALUE_LIST:
                        attribute_value = None
                    else:
                        attribute_value = attribute.get('attribute_value').strip()

                    # Insert new template attributes
                    new_attribute = ProjectLimitNumberTemplateAttribute(
                        template=template,
                        attribute_name=attribute.get('attribute_name'),
                        setting_type=setting_type,
                        attribute_value=attribute_value
                    )
                    new_attribute_list.append(new_attribute)
                if len(new_attribute_list) > 0:
                    ProjectLimitNumberTemplateAttribute.objects.bulk_create(new_attribute_list)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )
        except Exception as e:
            logger.error(f'Exception: {e}')
            return JsonResponse({'error_message': 'Internal server error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        return JsonResponse({}, status=HTTPStatus.CREATED)


class ProjectLimitNumberTemplatesViewUpdate(RdmPermissionMixin, UserPassesTestMixin, GuidFormView):
    """ Project Limit Number Template Detail page """
    template_name = 'project_limit_number_templates/update.html'
    object_type = 'project_limit_number_templates'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page or return HTTP 401
            self.raise_exception = False
            return False
        return self.is_super_admin

    def get_context_data(self, **kwargs):
        template_id = self.kwargs.get('template_id')
        template = ProjectLimitNumberTemplate.objects.filter(
            id=template_id,
            is_deleted=False,
            attributes__is_deleted=False
        ).values(
            'id',
            'template_name',
            'used_setting_number',
            'attributes__id',
            'attributes__attribute_name',
            'attributes__setting_type',
            'attributes__attribute_value'
        ).order_by('id').all()

        # Check template is NULL
        if len(template) == 0:
            raise Http404

        # Check template is used
        if template[0].get('used_setting_number') > 0:
            message = template[0].get('template_name') + ' is being used.'
            raise BadRequestException(message)

        data_template_list = []
        for item in template:
            data_template_list.append(
                {
                    'attribute_id': item.get('attributes__id'),
                    'attribute_name': item.get('attributes__attribute_name'),
                    'setting_type': SETTING_TYPE[item.get('attributes__setting_type') - 1],
                    'attribute_value': item.get('attributes__attribute_value'),
                }
            )

        return {
            'template_id': template_id,
            'template_name': template[0].get('template_name'),
            'data_template_list': data_template_list,
            'attribute_name_list': ATTRIBUTE_NAME_LIST,
            'setting_type_list': SETTING_TYPE,
        }

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except BadRequestException as e:
            return render_bad_request_response(request=request, error_msgs=e.args[0])
        except Exception as e:
            raise e


class ProjectLimitNumberTemplatesSettingSaveAvailabilityView(RdmPermissionMixin, UserPassesTestMixin, UpdateView):
    """ Project Limit Number Template Update Availability method """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin

    def handle_no_permission(self):
        if not self.raise_exception and self.request.method == 'PUT':
            # If request is PUT and user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(ProjectLimitNumberTemplatesSettingSaveAvailabilityView, self).handle_no_permission()

    def put(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            is_request_valid, message = utils.validate_file_json(request_body, 'update-availability-template-project-limit-number-setting-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': message}, status=HTTPStatus.BAD_REQUEST)

            data = request_body.get('data')

            template_id_list = [item.get('id') for item in data if item.get('id') is not None]
            # Validate id of template from request is not duplicate
            if len(template_id_list) != len(set(template_id_list)):
                return JsonResponse({'error_message': 'id is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            template_list = ProjectLimitNumberTemplate.objects.filter(id__in=template_id_list, is_deleted=False)
            if len(template_list) != len(template_id_list):
                return JsonResponse({'error_message': 'The template not exist.'}, status=HTTPStatus.BAD_REQUEST)

            input_data_map = {item.get('id'): item for item in data}
            with transaction.atomic():
                updates = []
                for template in template_list:
                    if template.used_setting_number > 0:
                        return JsonResponse({'error_message': template.template_name + ' is being used.'}, status=HTTPStatus.BAD_REQUEST)
                    input_data = input_data_map.get(template.id)
                    if input_data:
                        template.is_availability = input_data.get('is_availability')
                        template.modified = timezone.now()
                        updates.append(template)

                # Bulk update if there are changes
                if len(updates) > 0:
                    bulk_update(
                        updates,
                        update_fields=['is_availability', 'modified']
                    )
        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )
        except Exception as e:
            logger.error(f'Exception: {e}')
            return JsonResponse({'error_message': 'Internal server error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        return JsonResponse({}, status=HTTPStatus.OK)


class UpdateProjectLimitNumberTemplatesSettingView(RdmPermissionMixin, UserPassesTestMixin, UpdateView):
    """ Project Limit Number Template Update method """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page or return HTTP 401
            self.raise_exception = False
            return False
        return self.is_super_admin

    def handle_no_permission(self):
        if not self.raise_exception and self.request.method == 'PUT':
            # If request is PUT and user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(UpdateProjectLimitNumberTemplatesSettingView, self).handle_no_permission()

    def put(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            # Validate request data
            is_request_valid, message = utils.validate_file_json(request_body, 'update-template-project-limit-number-setting-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': message}, status=HTTPStatus.BAD_REQUEST)

            template_name = request_body.get('template_name')
            if template_name is None or not template_name.strip():
                return JsonResponse({'error_message': 'template_name is required.'}, status=HTTPStatus.BAD_REQUEST)

            # Trim template name
            template_name = template_name.strip()

            # Check duplicate
            attribute_list = request_body.get('attribute_list')
            attribute_id_list = [attr.get('id') for attr in attribute_list if attr.get('id') is not None]
            if len(attribute_id_list) != len(set(attribute_id_list)):
                return JsonResponse({'error_message': 'id is invalid.'}, status=HTTPStatus.BAD_REQUEST)
            template_id = self.kwargs.get('template_id')
            template = ProjectLimitNumberTemplate.objects.filter(
                id=template_id,
                is_deleted=False
            ).first()

            # Check template is None
            if not template:
                return JsonResponse({'error_message': 'The template not exist.'}, status=HTTPStatus.NOT_FOUND)

            # Check template is using
            if template.used_setting_number > 0:
                return JsonResponse({'error_message': template.template_name + ' is being used'}, status=HTTPStatus.BAD_REQUEST)

            # Check template name is exist
            if template.template_name != template_name:
                is_exist = ProjectLimitNumberTemplate.objects.filter(
                    template_name=template_name,
                    is_deleted=False
                ).exists()

                if is_exist:
                    return JsonResponse({'error_message': 'The template name already exists.'}, status=HTTPStatus.BAD_REQUEST)

            template_attribute_db_list = ProjectLimitNumberTemplateAttribute.objects.filter(
                template_id=template_id,
                is_deleted=False
            ).values(
                'id',
                'attribute_name',
                'setting_type',
                'attribute_value'
            ).all()

            # Check exist attribute
            template_attribute_id_db_list = [template_attribute.get('id') for template_attribute in template_attribute_db_list]
            for attribute in attribute_list:
                attribute_id = attribute.get('id')
                attribute_value = attribute.get('attribute_value') or ''
                if attribute_id is not None and attribute_id not in template_attribute_id_db_list:
                    return JsonResponse({'error_message': 'The attribute not exist.'}, status=HTTPStatus.BAD_REQUEST)
                if attribute.get('setting_type') in SETTING_TYPE_REQUIRED_VALUE_LIST and not attribute_value.strip():
                    return JsonResponse({'error_message': 'attribute_value is required.'}, status=HTTPStatus.BAD_REQUEST)
                if attribute.get('attribute_name') not in ATTRIBUTE_NAME_LIST:
                    return JsonResponse({'error_message': 'attribute_name is invalid.'}, status=HTTPStatus.BAD_REQUEST)
                if attribute.get('setting_type') in SETTING_TYPE_LIST_VALUE_LIST:
                    attribute_value_list = [item.strip() for item in attribute_value.split(',')]
                    if '' in attribute_value_list:
                        return JsonResponse({'error_message': 'attribute_value is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            attributes_to_update_list = []
            attributes_to_create_list = []
            attributes_id_is_deleted_list = []

            if len(attribute_id_list) != len(template_attribute_id_db_list):
                attributes_id_is_deleted_list = list(set(template_attribute_id_db_list) - set(attribute_id_list))

            for attribute in attribute_list:
                attribute_id = attribute.get('id')
                attribute_name = attribute.get('attribute_name')
                setting_type = attribute.get('setting_type')
                if setting_type in SETTING_TYPE_FREE_VALUE_LIST:
                    attribute_value = None
                else:
                    attribute_value = attribute.get('attribute_value', '').strip()

                if attribute_id is None:
                    # Prepare to create project_limit_number_template_attribute
                    new_attribute = ProjectLimitNumberTemplateAttribute(
                        template=template,
                        attribute_name=attribute_name,
                        setting_type=setting_type,
                        attribute_value=attribute_value
                    )
                    attributes_to_create_list.append(new_attribute)
                else:
                    # Prepare to update project_limit_number_template_attribute
                    template_attribute = ProjectLimitNumberTemplateAttribute(
                        template=template,
                        id=attribute_id,
                        attribute_name=attribute_name,
                        setting_type=setting_type,
                        attribute_value=attribute_value,
                        modified=timezone.now()
                    )
                    attributes_to_update_list.append(template_attribute)

            with transaction.atomic():
                if len(attributes_to_create_list) > 0:
                    ProjectLimitNumberTemplateAttribute.objects.bulk_create(attributes_to_create_list)

                if len(attributes_to_update_list) > 0:
                    bulk_update(attributes_to_update_list, update_fields=['attribute_name', 'setting_type', 'attribute_value', 'modified'])

                if len(attributes_id_is_deleted_list) > 0:
                    ProjectLimitNumberTemplateAttribute.objects.filter(
                        id__in=attributes_id_is_deleted_list,
                    ).update(is_deleted=True, modified=timezone.now())

                if template.template_name != template_name:
                    template.template_name = template_name
                template.modified = timezone.now()
                template.save()

        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )
        except Exception as e:
            logger.error(f'Exception: {e}')
            return JsonResponse({'error_message': 'Internal server error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        return JsonResponse({}, status=HTTPStatus.OK)


class DeleteProjectLimitNumberTemplatesSettingView(RdmPermissionMixin, UserPassesTestMixin, DeleteView):
    """ Project Limit Number Template Delete method """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page or return HTTP 401
            self.raise_exception = False
            return False
        return self.is_super_admin

    def handle_no_permission(self):
        if not self.raise_exception and self.request.method == 'DELETE':
            # If request is DELETE and user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(DeleteProjectLimitNumberTemplatesSettingView, self).handle_no_permission()

    def delete(self, request, *args, **kwargs):
        """Delete project limit number setting and update related data"""
        try:
            template_id = self.kwargs.get('template_id')

            template = ProjectLimitNumberTemplate.objects.filter(
                id=template_id,
                is_deleted=False
            ).first()

            if template is None:
                return JsonResponse(
                    {'error_message': 'Template not found'},
                    status=HTTPStatus.NOT_FOUND
                )

            if template.used_setting_number > 0:
                return JsonResponse(
                    {'error_message': template.template_name + ' is being used'},
                    status=HTTPStatus.BAD_REQUEST
                )

            with transaction.atomic():
                ProjectLimitNumberTemplate.objects.filter(
                    id=template_id
                ).update(is_deleted=True, modified=timezone.now())

                ProjectLimitNumberTemplateAttribute.objects.filter(
                    template_id=template_id
                ).update(is_deleted=True, modified=timezone.now())

        except Exception as e:
            logger.error(f'Exception: {e}')
            return JsonResponse(
                {'error_message': 'Internal server error'},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return JsonResponse({}, status=HTTPStatus.OK)
