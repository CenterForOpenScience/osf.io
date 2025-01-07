from __future__ import unicode_literals

import json
import math
from http import HTTPStatus

from django.core.exceptions import PermissionDenied
from django.db import transaction, connection
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views import View
from django_bulk_update.helper import bulk_update
from django.utils.translation import ugettext_lazy as _
from django.views.generic import UpdateView, ListView, DeleteView, TemplateView

from admin.base.utils import render_bad_request_response
from admin.project_limit_number import utils
from admin.rdm.utils import RdmPermissionMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from osf.models import Institution, ProjectLimitNumberSetting, ProjectLimitNumberSettingAttribute, ProjectLimitNumberTemplate, \
    ProjectLimitNumberTemplateAttribute, ProjectLimitNumberDefault, AbstractNode, UserExtendedData
from django.db.models import F, Max, Value, Count
from admin.base import settings
from django.http import Http404, JsonResponse
import logging

logger = logging.getLogger(__name__)

PROJECT_LIMIT_NUMBER_SELECT_LIST = range(settings.PROJECT_LIMIT_NUMBER + 1)
PAGE_SIZE_LIST = [10, 25, 50]
LIST_VALUE_SETTING_TYPE_LIST = [item[0] for item in settings.SETTING_TYPE if item[1].startswith('list_value')]
FIXED_VALUE_SETTING_TYPE_LIST = [item[0] for item in settings.SETTING_TYPE if item[1].startswith('fixed_value')]


class ProjectLimitNumberSettingListView(RdmPermissionMixin, UserPassesTestMixin, ListView):
    """ Project Limit Number Setting List page """
    template_name = 'project_limit_number/list.html'
    object_type = 'project_limit_number'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def get_queryset(self):
        """ Get project limit number setting queryset """
        return ProjectLimitNumberSetting.objects.filter(is_deleted=False).select_related('template').order_by('priority')

    def get_context_data(self, **kwargs):
        institution_id = self.request.GET.get('institution_id')
        page_size = self.request.GET.get('page_size')
        # Trim query params
        institution_id = institution_id.strip() if institution_id and len(institution_id.strip()) > 0 else None
        page_size = page_size.strip() if page_size and len(page_size.strip()) > 0 else 10

        if self.is_super_admin:
            institution_list = Institution.objects.filter(is_deleted=False).order_by('id')
            selected_institution = institution_list.filter(id=institution_id).first()
            if not selected_institution:
                # If user is super admin and institution_id is None then return page with only institution list
                kwargs['institutions'] = institution_list
                return super(ProjectLimitNumberSettingListView, self).get_context_data(**kwargs)
        else:
            selected_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
            selected_institution_id = selected_institution.id if selected_institution is not None else None
            if institution_id and selected_institution_id != int(institution_id):
                raise PermissionDenied('You don\'t have permission to access this page')
            institution_list = [selected_institution]

        query_set = self.get_queryset().filter(institution=selected_institution)

        # Get project_limit_number_default
        project_limit_number_default = selected_institution.project_limit_number_default.first()
        project_limit_number_default_value = project_limit_number_default.project_limit_number if project_limit_number_default is not None else utils.NO_LIMIT
        # Get page_size from request
        _, page, query_set, _ = self.paginate_queryset(query_set, page_size)
        data = []
        for setting in query_set.all():
            data.append(
                {
                    'id': setting.id,
                    'priority': setting.priority,
                    'template_name': setting.template.template_name,
                    'setting_name': setting.name,
                    'memo': setting.memo,
                    'is_availability': setting.is_availability,
                    'created': setting.created,
                    'modified': setting.modified
                }
            )
        kwargs['project_limit_number_setting_list'] = data
        kwargs['page'] = page
        kwargs['page_size'] = int(page_size)
        kwargs['institutions'] = institution_list
        kwargs['selected_institution'] = selected_institution
        kwargs['is_admin'] = self.is_institutional_admin
        kwargs['project_limit_number_default_list'] = PROJECT_LIMIT_NUMBER_SELECT_LIST
        kwargs['project_limit_number_default_value'] = project_limit_number_default_value
        return super(ProjectLimitNumberSettingListView, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        institution_id = self.request.GET.get('institution_id')
        page_size = self.request.GET.get('page_size')
        # Trim query params
        institution_id = institution_id.strip() if institution_id else None
        page_size = page_size.strip() if page_size else None

        # Check if institution_id is not None
        if institution_id:
            # Try casting institution_id to integer
            try:
                institution_id = int(institution_id)
            except ValueError:
                # If institution id is not a number then return HTTP 400
                return render_bad_request_response(request=request, error_msgs='The institution id is invalid.')

        # Check if page_size is not None
        if page_size:
            # Try casting page_size to integer
            try:
                page_size = int(page_size)
                if page_size not in PAGE_SIZE_LIST:
                    # If page size is not in PAGE_SIZE_LIST then return HTTP 400
                    return render_bad_request_response(request=request, error_msgs='The page size is invalid.')
            except ValueError:
                # If page size is not a number then return HTTP 400
                return render_bad_request_response(request=request, error_msgs='The page size is invalid.')

        # Check if institution with institution_id exists
        if institution_id and not Institution.objects.filter(id=institution_id, is_deleted=False).exists():
            return render_bad_request_response(request=request, error_msgs='The institution not exist.')

        return super(ProjectLimitNumberSettingListView, self).get(request, *args, **kwargs)


class SaveProjectLimitNumberDefaultView(RdmPermissionMixin, UserPassesTestMixin, UpdateView):
    """ Save project limit number default API view """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception:
            # If user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(SaveProjectLimitNumberDefaultView, self).handle_no_permission()

    def put(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            is_request_valid, error_message = utils.validate_file_json(request_body, 'project-limit-number-default-save-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': error_message}, status=HTTPStatus.BAD_REQUEST)

            project_limit_number = request_body.get('project_limit_number', utils.NO_LIMIT)
            if project_limit_number > settings.PROJECT_LIMIT_NUMBER:
                return JsonResponse({'error_message': 'project_limit_number is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            # Check if institution exists
            institution_id = request_body.get('institution_id')
            if not Institution.objects.filter(id=institution_id, is_deleted=False).exists():
                return JsonResponse({'error_message': 'The institution not exist.'}, status=HTTPStatus.BAD_REQUEST)

            # Handle admin permissions
            if self.is_admin:
                first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
                if not first_affiliated_institution or first_affiliated_institution.id != institution_id:
                    return JsonResponse({'error_message': 'Forbidden'}, status=HTTPStatus.FORBIDDEN)

            # Get project limit number default by institution_id
            existing_item = ProjectLimitNumberDefault.objects.filter(institution_id=institution_id).first()
            if not existing_item:
                # Create project limit number default
                ProjectLimitNumberDefault.objects.create(
                    institution_id=institution_id,
                    project_limit_number=project_limit_number
                )
            else:
                # Update project limit number default
                existing_item.project_limit_number = project_limit_number
                existing_item.save()
        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )

        return JsonResponse({}, status=HTTPStatus.OK)


class ProjectLimitNumberSettingSaveAvailabilityView(RdmPermissionMixin, UserPassesTestMixin, UpdateView):
    """ Save Project Limit Number Setting Availability API View """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception:
            # If user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(ProjectLimitNumberSettingSaveAvailabilityView, self).handle_no_permission()

    def put(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            is_request_valid, error_message = utils.validate_file_json(request_body, 'project-limit-number-setting-save-availability-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': error_message}, status=HTTPStatus.BAD_REQUEST)

            institution_id = request_body.get('institution_id')
            setting_list = request_body.get('setting_list')
            setting_id_list = [item.get('id') for item in setting_list if item.get('id') is not None]
            priority_list = [item.get('priority') for item in setting_list if item.get('priority') is not None]
            if len(set(setting_id_list)) != len(setting_id_list):
                return JsonResponse({'error_message': 'id is invalid.'}, status=HTTPStatus.BAD_REQUEST)
            if len(set(priority_list)) != len(priority_list):
                return JsonResponse({'error_message': 'priority is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            if not Institution.objects.filter(id=institution_id, is_deleted=False).exists():
                return JsonResponse({'error_message': 'The institution not exist.'}, status=HTTPStatus.BAD_REQUEST)

            if self.is_admin:
                first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
                if not first_affiliated_institution or first_affiliated_institution.id != institution_id:
                    return JsonResponse({'error_message': 'Forbidden'}, status=HTTPStatus.FORBIDDEN)

            input_data_map = {item.get('id'): item for item in setting_list if item.get('id')}
            db_setting_list = list(ProjectLimitNumberSetting.objects.filter(institution_id=institution_id, id__in=setting_id_list, is_deleted=False))
            if len(db_setting_list) != len(setting_list):
                return JsonResponse({'error_message': 'The setting not exist.'}, status=HTTPStatus.BAD_REQUEST)
            current_priorities = [setting.priority for setting in db_setting_list]
            with transaction.atomic():
                updated_setting_list = []
                # Prepare data for bulk update
                for setting in db_setting_list:
                    # Get request setting item by setting id
                    input_data = input_data_map.get(setting.id)
                    input_priority = input_data.get('priority')
                    if input_priority not in current_priorities:
                        return JsonResponse({'error_message': 'The priority is invalid.'}, status=HTTPStatus.BAD_REQUEST)
                    # Set setting item by input data
                    setting.priority = input_data.get('priority')
                    setting.is_availability = input_data.get('is_availability')
                    setting.modified = timezone.now()
                    updated_setting_list.append(setting)

                # Bulk update if there are any changes in setting
                if updated_setting_list:
                    bulk_update(
                        updated_setting_list,
                        update_fields=['priority', 'is_availability', 'modified']
                    )
        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )

        return JsonResponse({}, status=HTTPStatus.OK)


class DeleteProjectLimitNumberSettingView(RdmPermissionMixin, UserPassesTestMixin, DeleteView):
    """ Delete Project Limit Number Setting API View """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception:
            # If user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(DeleteProjectLimitNumberSettingView, self).handle_no_permission()

    def delete(self, request, *args, **kwargs):
        """Delete project limit number setting and update related data"""
        try:
            # Get setting id
            setting_id = kwargs.get('setting_id')

            # Get the setting to be deleted and verify it exists
            setting_to_delete = ProjectLimitNumberSetting.objects.filter(
                id=setting_id,
                is_deleted=False
            ).select_related('template').first()

            if setting_to_delete is None:
                return JsonResponse({'error_message': 'The setting not exist.'}, status=HTTPStatus.NOT_FOUND)

            # Handle admin permissions
            institution_id = setting_to_delete.institution.id if setting_to_delete.institution else None
            if self.is_admin:
                first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
                if not first_affiliated_institution or first_affiliated_institution.id != institution_id:
                    return JsonResponse({'error_message': 'Forbidden'}, status=HTTPStatus.FORBIDDEN)

            # Store the priority and template for later use
            current_priority = setting_to_delete.priority
            template = setting_to_delete.template

            with transaction.atomic():
                # Mark the setting as deleted
                setting_to_delete.is_deleted = True
                setting_to_delete.save()

                # Mark all related attributes as deleted
                ProjectLimitNumberSettingAttribute.objects.filter(
                    setting_id=setting_id,
                    is_deleted=False
                ).update(is_deleted=True, modified=timezone.now())

                # Decrease the used_setting_number in the template
                template.used_setting_number = template.used_setting_number - 1
                template.save()

                # Update priorities of other settings
                ProjectLimitNumberSetting.objects.filter(
                    institution_id=institution_id,
                    priority__gt=current_priority,
                    is_deleted=False
                ).update(priority=F('priority') - 1, modified=timezone.now())
        except Exception as e:
            raise e

        return JsonResponse({}, status=HTTPStatus.OK)


class ProjectLimitNumberSettingCreateView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """ Create Project Limit Number Setting View """
    template_name = 'project_limit_number/create.html'
    object_type = 'project_limit_number'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page or return HTTP 401
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception and self.request.method == 'POST':
            # If request is POST and user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(ProjectLimitNumberSettingCreateView, self).handle_no_permission()

    def get(self, request, *args, **kwargs):
        """ Get data for create view """
        institution_id = self.request.GET.get('institution_id')
        template_id = self.request.GET.get('template_id')
        # Trim query params
        institution_id = institution_id.strip() if institution_id and len(institution_id.strip()) > 0 else None
        template_id = template_id.strip() if template_id and len(template_id.strip()) > 0 else None

        # Early validation for super admin
        if institution_id is None and self.is_super_admin:
            return render_bad_request_response(request=request, error_msgs='The institution id is required.')

        # Validate and process institution_id
        institution = None
        if institution_id:
            # Try casting institution_id to integer
            try:
                institution_id = int(institution_id)
            except ValueError:
                return render_bad_request_response(request=request, error_msgs='The institution id is invalid.')

            # Get institution by institution_id
            institution = Institution.objects.filter(id=institution_id, is_deleted=False).first()
            if not institution:
                return render_bad_request_response(request=request, error_msgs='The institution not exist.')

        # Validate template_id
        if template_id:
            # Try casting template_id to integer
            try:
                template_id = int(template_id)
            except ValueError:
                return render_bad_request_response(request=request, error_msgs='The template id is invalid.')

        # Handle admin permissions
        if self.is_admin:
            first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
            if institution_id and (not first_affiliated_institution or first_affiliated_institution.id != institution_id):
                raise PermissionDenied('You don\'t have permission to access this page')
            institution = first_affiliated_institution

        # Get template data
        template_list = ProjectLimitNumberTemplate.objects.filter(is_availability=True, is_deleted=False).order_by('-id')

        if not template_id:
            # If template_id is None, return response data
            response_data = {
                'template_list': template_list,
                'template_attribute_list': [],
                'institution': institution,
                'project_limit_number_select_list': PROJECT_LIMIT_NUMBER_SELECT_LIST,
                'template_id': None
            }
            return self.render_to_response(response_data)

        # Get selected template
        selected_template = template_list.filter(id=template_id).first()

        if template_id and not selected_template:
            return render_bad_request_response(request=request, error_msgs='The template not exist.')

        template_attribute_list = []
        if selected_template:
            template_attribute_list = selected_template.attributes.filter(is_deleted=False).order_by('id').values(
                'id', 'attribute_name', 'setting_type', 'attribute_value')
            for data in template_attribute_list:
                attribute_value = data.get('attribute_value')
                setting_type = data.get('setting_type')
                if attribute_value:
                    data['attribute_value'] = (
                        [item.strip() for item in attribute_value.split(',')]
                        if setting_type in LIST_VALUE_SETTING_TYPE_LIST
                        else attribute_value.strip()
                    )
                data['setting_name'] = dict(settings.SETTING_TYPE).get(setting_type)

        # Prepare response data
        response_data = {
            'template_list': template_list,
            'template_attribute_list': template_attribute_list,
            'institution': institution,
            'project_limit_number_select_list': PROJECT_LIMIT_NUMBER_SELECT_LIST,
            'template_id': selected_template.id if selected_template else None
        }

        return self.render_to_response(response_data)

    def post(self, request, *args, **kwargs):
        """ Create new project limit number setting """
        try:
            request_body = json.loads(request.body)
            is_request_valid, error_message = utils.validate_file_json(request_body, 'create-project-limit-number-setting-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': error_message}, status=HTTPStatus.BAD_REQUEST)

            template_id = request_body.get('template_id')
            institution_id = request_body.get('institution_id')
            name = request_body.get('name').strip()
            memo = request_body.get('memo')
            # Trim memo
            memo = memo.strip() if memo is not None else None
            project_limit_number = request_body.get('project_limit_number', utils.NO_LIMIT)
            attribute_list = request_body.get('attribute_list')

            # If trimmed name is empty then return HTTP 400
            if not name:
                return JsonResponse({'error_message': 'name is required.'}, status=HTTPStatus.BAD_REQUEST)

            # If project_limit_number is more than PROJECT_LIMIT_NUMBER then return HTTP 400
            if project_limit_number > settings.PROJECT_LIMIT_NUMBER:
                return JsonResponse({'error_message': 'project_limit_number is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            # If attribute_list has duplicated attribute_id then return HTTP 400
            attribute_id_set = set([item.get('attribute_id') for item in attribute_list])
            if len(attribute_list) != len(attribute_id_set):
                return JsonResponse({'error_message': 'attribute_id is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            if not Institution.objects.filter(id=institution_id, is_deleted=False).exists():
                return JsonResponse({'error_message': 'The institution not exist.'}, status=HTTPStatus.BAD_REQUEST)
            if self.is_admin:
                first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
                if institution_id and (not first_affiliated_institution or first_affiliated_institution.id != institution_id):
                    return JsonResponse({'error_message': 'Forbidden'}, status=HTTPStatus.FORBIDDEN)

            # Get setting by name and institution_id
            is_setting_exist = ProjectLimitNumberSetting.objects.filter(institution_id=institution_id, name=name, is_deleted=False).exists()
            if is_setting_exist:
                return JsonResponse({'error_message': 'The setting name already exists.'}, status=HTTPStatus.BAD_REQUEST)

            # Get template and template attribute by template_id and is_availability
            template = ProjectLimitNumberTemplate.objects.filter(id=template_id, is_availability=True, is_deleted=False).first()
            if template is None:
                return JsonResponse({'error_message': 'The template not exist.'}, status=HTTPStatus.BAD_REQUEST)
            template_attribute_list = list(ProjectLimitNumberTemplateAttribute.objects.filter(template=template, is_deleted=False))
            if len(template_attribute_list) != len(attribute_list):
                return JsonResponse({'error_message': 'The attribute list is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            # Check attribute_list
            for attribute in attribute_list:
                template_attribute = next((item for item in template_attribute_list if item.id == attribute.get('attribute_id')), None)
                if template_attribute is None:
                    # If attribute_id not exist in template_attributes then return 400
                    return JsonResponse({'error_message': 'The attribute not exist.'}, status=HTTPStatus.BAD_REQUEST)
                if template_attribute.setting_type in FIXED_VALUE_SETTING_TYPE_LIST and attribute.get('attribute_value') != template_attribute.attribute_value:
                    # If template_attributes[i].setting_type is fixed value and attribute_value != template_attributes[i].attribute_value then return 400
                    return JsonResponse({'error_message': 'The attribute value is invalid.'}, status=HTTPStatus.BAD_REQUEST)
                db_attribute_value_list = []
                if template_attribute.attribute_value:
                    # Split template attribute value by comma
                    db_attribute_value_list = [item.strip() for item in template_attribute.attribute_value.split(',')]
                if template_attribute.setting_type in LIST_VALUE_SETTING_TYPE_LIST and attribute.get('attribute_value') not in db_attribute_value_list:
                    # If template_attributes[i].setting_type is list value and attribute_value not exist in template_attributes[i].attribute_value then return 400
                    return JsonResponse({'error_message': 'The attribute value is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            with transaction.atomic():
                # Insert new setting
                max_priority = ProjectLimitNumberSetting.objects.filter(
                    institution_id=institution_id,
                    is_deleted=False
                ).aggregate(max_priority=Coalesce(Max('priority'), Value(0)))['max_priority']
                new_setting = ProjectLimitNumberSetting(
                    template=template,
                    institution_id=institution_id,
                    name=name,
                    memo=memo,
                    project_limit_number=project_limit_number,
                    priority=max_priority + 1
                )
                new_setting.save()

                # Insert new setting attributes
                new_attribute_list = []
                for attribute in attribute_list:
                    new_attribute = ProjectLimitNumberSettingAttribute(
                        setting=new_setting,
                        attribute_id=attribute.get('attribute_id'),
                        attribute_value=attribute.get('attribute_value')
                    )
                    new_attribute_list.append(new_attribute)
                ProjectLimitNumberSettingAttribute.objects.bulk_create(new_attribute_list)

                # Update used_setting_number of template
                template.used_setting_number += 1
                template.save()
        except json.JSONDecodeError:
            # Return HTTP 400 if request body cannot be parsed to JSON
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )

        return JsonResponse({}, status=HTTPStatus.CREATED)


class ProjectLimitNumberSettingDetailView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """ Project Limit Number Setting Detail View"""
    template_name = 'project_limit_number/detail.html'
    object_type = 'project_limit_number'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def get_setting_data(self, setting_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.name, s.memo, s.project_limit_number, t.template_name,
                       sa.id AS attribute_id, sa.attribute_value,
                       ta.attribute_name, ta.setting_type, ta.attribute_value as template_attribute_value,
                       i.id as institution_id, i.name AS institution_name
                FROM osf_project_limit_number_setting AS s
                JOIN osf_project_limit_number_template AS t
                    ON s.template_id = t.id
                JOIN osf_project_limit_number_setting_attribute AS sa
                    ON s.id = sa.setting_id
                JOIN osf_project_limit_number_template_attribute AS ta
                    ON sa.attribute_id = ta.id
                JOIN osf_institution AS i
                    ON s.institution_id = i.id
                WHERE s.id = %s
                   AND s.is_deleted IS FALSE
                ORDER BY attribute_id ASC
            """, [setting_id])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get(self, request, *args, **kwargs):
        """ Get data for setting detail view """
        setting_id = kwargs.get('setting_id')
        # Get setting by setting_id
        setting_data_list = self.get_setting_data(setting_id)
        if not setting_data_list:
            raise Http404(_('The setting not exist.'))

        # Handle admin permissions
        first_setting_data = setting_data_list[0]
        institution_id = first_setting_data.get('institution_id')
        if self.is_admin:
            first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
            if not first_affiliated_institution or first_affiliated_institution.id != institution_id:
                raise PermissionDenied('You don\'t have permission to access this page')

        setting_attribute_list = []
        for data in setting_data_list:
            template_attribute_value = data.get('template_attribute_value', '')
            setting_type = data.get('setting_type')
            attribute_value_select_list = None
            if setting_type in LIST_VALUE_SETTING_TYPE_LIST:
                attribute_value_select_list = [item.strip() for item in template_attribute_value.split(',')]
            setting_attribute_list.append({
                'attribute_id': data.get('attribute_id'),
                'attribute_name': data.get('attribute_name'),
                'setting_type': setting_type,
                'setting_name': dict(settings.SETTING_TYPE).get(setting_type),
                'attribute_value_select_list': attribute_value_select_list,
                'attribute_value': data.get('attribute_value'),
            })
        setting = {
            'id': first_setting_data.get('id'),
            'name': first_setting_data.get('name'),
            'memo': first_setting_data.get('memo'),
            'project_limit_number': first_setting_data.get('project_limit_number'),
        }
        response_data = {
            'template_name': first_setting_data.get('template_name'),
            'setting_attribute_list': setting_attribute_list,
            'setting': setting,
            'institution_id': institution_id,
            'institution_name': first_setting_data.get('institution_name'),
            'project_limit_number_select_list': PROJECT_LIMIT_NUMBER_SELECT_LIST,
        }
        return self.render_to_response(response_data)


class UpdateProjectLimitNumberSettingView(RdmPermissionMixin, UserPassesTestMixin, UpdateView):
    """ Update Project Limit Number Setting API View """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception:
            # If user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(UpdateProjectLimitNumberSettingView, self).handle_no_permission()

    def put(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            is_request_valid, error_message = utils.validate_file_json(request_body, 'update-project-limit-number-setting-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': error_message}, status=HTTPStatus.BAD_REQUEST)

            setting_id = kwargs.get('setting_id')
            name = request_body.get('name').strip()
            memo = request_body.get('memo')
            # Trim memo
            memo = memo.strip() if memo is not None else None
            project_limit_number = request_body.get('project_limit_number', utils.NO_LIMIT)
            attribute_list = request_body.get('attribute_list')

            # If setting_id is None then return HTTP 400
            if setting_id is None:
                return JsonResponse({'error_message': 'setting_id is required.'}, status=HTTPStatus.BAD_REQUEST)

            # If trimmed name is empty then return HTTP 400
            if not name:
                return JsonResponse({'error_message': 'name is required.'}, status=HTTPStatus.BAD_REQUEST)

            # If project_limit_number is more than PROJECT_LIMIT_NUMBER then return HTTP 400
            if project_limit_number > settings.PROJECT_LIMIT_NUMBER:
                return JsonResponse({'error_message': 'project_limit_number is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            # If attribute_list has duplicated attribute_id then return HTTP 400
            attribute_id_set = set([item.get('id') for item in attribute_list])
            if len(attribute_list) != len(attribute_id_set):
                return JsonResponse({'error_message': 'id is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            setting = ProjectLimitNumberSetting.objects.filter(id=setting_id, is_deleted=False).first()
            if setting is None:
                return JsonResponse({'error_message': 'The setting not exist.'}, status=HTTPStatus.NOT_FOUND)

            setting_attribute_list = list(setting.attributes.filter(is_deleted=False).select_related('attribute'))
            template_attribute_list = [setting_attribute.attribute for setting_attribute in setting_attribute_list]

            institution_id = setting.institution.id if setting.institution else None
            if self.is_admin:
                first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
                if not first_affiliated_institution or first_affiliated_institution.id != institution_id:
                    return JsonResponse({'error_message': 'Forbidden'}, status=HTTPStatus.FORBIDDEN)

            if name != setting.name:
                # If name is changed then check if name is already exists
                setting_list = ProjectLimitNumberSetting.objects.filter(institution_id=institution_id, name=name, is_deleted=False)
                if setting_list.exists():
                    return JsonResponse({'error_message': 'The setting name already exists.'}, status=HTTPStatus.BAD_REQUEST)

            if len(attribute_list) != len(setting_attribute_list) or len(attribute_list) != len(template_attribute_list):
                return JsonResponse({'error_message': 'The attribute list is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            # Check attribute_list
            for attribute in attribute_list:
                setting_attribute = next((item for item in setting_attribute_list if item.id == attribute.get('id')), None)
                if setting_attribute is None:
                    # If attribute_id not exist in template_attributes then return 400
                    return JsonResponse({'error_message': 'The attribute not exist.'}, status=HTTPStatus.BAD_REQUEST)

                template_attribute = next((item for item in template_attribute_list if item.id == setting_attribute.attribute_id), None)
                if template_attribute.setting_type in FIXED_VALUE_SETTING_TYPE_LIST and attribute.get('attribute_value') != template_attribute.attribute_value:
                    # If template_attributes[i].setting_type is fixed value and attribute_value != template_attributes[i].attribute_value then return 400
                    return JsonResponse({'error_message': 'The attribute value is invalid.'}, status=HTTPStatus.BAD_REQUEST)
                db_attribute_value_list = []
                if template_attribute.attribute_value:
                    # Split template attribute value by comma
                    db_attribute_value_list = [item.strip() for item in template_attribute.attribute_value.split(',')]
                if template_attribute.setting_type in LIST_VALUE_SETTING_TYPE_LIST and attribute.get('attribute_value') not in db_attribute_value_list:
                    # If template_attributes[i].setting_type is list value and attribute_value not exist in template_attributes[i].attribute_value then return 400
                    return JsonResponse({'error_message': 'The attribute value is invalid.'}, status=HTTPStatus.BAD_REQUEST)

            with transaction.atomic():
                # Update setting
                setting.name = name
                setting.memo = memo
                setting.project_limit_number = project_limit_number
                setting.save()

                # Update setting attributes
                updated_attribute_list = []
                for attribute in attribute_list:
                    setting_attribute = ProjectLimitNumberSettingAttribute(
                        id=attribute.get('id'),
                        attribute_value=attribute.get('attribute_value'),
                        modified=timezone.now()
                    )
                    updated_attribute_list.append(setting_attribute)
                bulk_update(updated_attribute_list, update_fields=['attribute_value', 'modified'])
        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )

        return JsonResponse({}, status=HTTPStatus.OK)


class UserListView(RdmPermissionMixin, UserPassesTestMixin, View):
    """ User list quota info screen for an institution that is not using NII Storage. """
    paginate_by = 10
    institution_id = None
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        return self.is_super_admin or self.is_institutional_admin

    def handle_no_permission(self):
        """ Handle user has no permission """
        if not self.raise_exception:
            # If user is not authenticated then return HTTP 401
            return JsonResponse(
                {'error_message': 'Authentication credentials were not provided.'},
                status=HTTPStatus.UNAUTHORIZED
            )
        return super(UserListView, self).handle_no_permission()

    def post(self, request, *args, **kwargs):
        try:
            request_body = json.loads(request.body)
            is_request_valid, error_message = utils.validate_file_json(request_body, 'get-project-limit-user-list-schema.json')
            if not is_request_valid:
                return JsonResponse({'error_message': error_message}, status=HTTPStatus.BAD_REQUEST)

            page = request_body.get('page')
            if page is None:
                page = '1'
            institution_id = request_body.get('institution_id')
            attribute_list = request_body.get('attribute_list', [])

            # If institution_id is not exist then return HTTP 400
            if not Institution.objects.filter(id=institution_id, is_deleted=False).exists():
                return JsonResponse({'error_message': 'The institution not exist.'}, status=HTTPStatus.BAD_REQUEST)

            # Handle admin permissions
            if self.is_admin:
                first_affiliated_institution = self.request.user.affiliated_institutions.filter(is_deleted=False).first()
                if not first_affiliated_institution or first_affiliated_institution.id != institution_id:
                    return JsonResponse({'error_message': 'Forbidden'}, status=HTTPStatus.FORBIDDEN)

            # Combine logic condition in attribute list
            logic_condition_query_string = ''
            include_osf_user_query_string = ''
            logic_condition_params = []
            include_osf_user_params = []
            for attribute in attribute_list:
                if attribute.get('attribute_name') not in settings.ATTRIBUTE_NAME_LIST:
                    return JsonResponse({'error_message': 'attribute_name is invalid.'}, status=HTTPStatus.BAD_REQUEST)
                if attribute.get('attribute_name') == utils.MAIL_GRDM:
                    # Get query from osf_user table instead
                    if len(include_osf_user_query_string) > 0:
                        include_osf_user_query_string += ' AND '
                    query_string, params = utils.generate_logic_condition_from_attribute(attribute)
                    include_osf_user_query_string += query_string
                    include_osf_user_params.extend(params)
                else:
                    # Get query from osf_userextendeddata table
                    if len(logic_condition_query_string) > 0:
                        logic_condition_query_string += ' AND '
                    query_string, params = utils.generate_logic_condition_from_attribute(attribute)
                    logic_condition_query_string += query_string
                    logic_condition_params.extend(params)

            count = self.count_user_met_logic_condition(institution_id, logic_condition_query_string,
                                                        include_osf_user_query_string, logic_condition_params, include_osf_user_params)
            if count == 0:
                return JsonResponse({'user_list': [], 'total': 0}, status=HTTPStatus.OK)

            # Convert string to int
            if page == 'last':
                # If page is 'last' then get the last page
                page = math.ceil(count / self.paginate_by)
            else:
                page = int(page)

            user_list = self.get_user_list_met_logic_condition(institution_id, page, logic_condition_query_string,
                                                               include_osf_user_query_string, logic_condition_params, include_osf_user_params)
            if len(user_list) == 0:
                return JsonResponse({'user_list': [], 'total': count}, status=HTTPStatus.OK)

            # Get the list setting for institution
            setting_list = ProjectLimitNumberSetting.objects.filter(
                institution_id=institution_id,
                is_availability=True,
                is_deleted=False
            ).order_by('priority').all()
            setting_id_list = [s.id for s in setting_list]
            # Get setting list attribute by setting
            all_setting_attribute_list = (ProjectLimitNumberSettingAttribute.objects.select_related(
                'attribute'
            ).filter(
                setting_id__in=setting_id_list,
                is_deleted=False
            ).annotate(
                setting_type=F('attribute__setting_type'),
                attribute_name=F('attribute__attribute_name'),
                setting_id=F('setting_id')
            ).order_by('id').values(
                'id',
                'attribute_name',
                'setting_type',
                'attribute_value',
                'setting_id'
            ))

            setting_attributes_dict = {}
            for setting_attribute in all_setting_attribute_list:
                setting_id = setting_attribute.get('setting_id')
                setting_attributes_dict.setdefault(setting_id, []).append(setting_attribute)

            user_list_met_condition = []
            user_list_response = []
            user_extended_data_attributes = UserExtendedData.objects.filter(user_id__in=[user.get('id') for user in user_list])
            # Check if user met any logic condition from setting list
            for setting in setting_list:
                if len(user_list) > 0:
                    project_limit_number = setting.project_limit_number
                    for user in user_list:
                        user_extended_data_attribute = next((p for p in user_extended_data_attributes if p.user_id == user.get('id')), None)
                        # Check if user met the logic condition from this setting
                        is_user_met_condition = utils.check_logic_condition(user, setting_attributes_dict.get(setting.id, []), user_extended_data_attribute)
                        if is_user_met_condition:
                            user['project_limit_number'] = project_limit_number
                            user_list_met_condition.append(user.get('guid'))
                            user_list_response.append(user)
                    # Remove user that met condition
                    user_list = [item for item in user_list if item.get('guid') not in user_list_met_condition]

            if len(user_list) > 0:
                # Use project limit number default value for remaining users that does not met any conditions
                project_limit_number_default = ProjectLimitNumberDefault.objects.filter(institution_id=institution_id).first()
                project_limit_number_default_value = (project_limit_number_default.project_limit_number
                                                      if project_limit_number_default is not None else utils.NO_LIMIT)
                for user in user_list:
                    user['project_limit_number'] = project_limit_number_default_value
                    user_list_response.append(user)

            # Get created project number list by user id list
            user_id_list = [user.get('id') for user in user_list_response]
            created_project_number_list = (
                AbstractNode.objects.filter(
                    type='osf.node',
                    creator_id__in=user_id_list,
                    is_deleted=False
                )
                .values('creator_id')
                .annotate(
                    user_id=F('creator_id'),
                    created_project_number=Count('creator_id')
                )
                .values('user_id', 'created_project_number'))

            # Set created_project_number for each user if have (default is 0)
            created_project_number_map = {item.get('user_id'): item.get('created_project_number') for item in created_project_number_list}
            for user in user_list_response:
                user['created_project_number'] = created_project_number_map.get(user.get('id'), 0)

            return JsonResponse({'user_list': user_list_response, 'total': count}, status=HTTPStatus.OK)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error_message': 'The request body is invalid.'},
                status=HTTPStatus.BAD_REQUEST
            )

    def count_user_met_logic_condition(self, institution_id, logic_condition_query_string,
                                       include_osf_user_query_string, logic_condition_params, include_osf_user_params):
        query = ''
        if len(logic_condition_query_string) > 0:
            query += f"""
                WITH userextendeddata AS (
                    SELECT DISTINCT user_id
                    FROM osf_userextendeddata
                    WHERE {logic_condition_query_string} )
            """

        query += """
            SELECT COUNT(*)
            FROM osf_osfuser AS u
            JOIN osf_guid AS g
                ON u.id = g.object_id
                AND g.content_type_id = 1
            JOIN osf_osfuser_affiliated_institutions AS ui
                ON u.id = ui.osfuser_id
            """
        if len(logic_condition_query_string) > 0:
            query += ' JOIN userextendeddata ux ON u.id = ux.user_id'

        query += """
            WHERE ui.institution_id = %s
            """

        if len(include_osf_user_query_string) > 0:
            query += f' AND {include_osf_user_query_string}'

        # Execute the raw query
        params = logic_condition_params + [institution_id] + include_osf_user_params
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            count = cursor.fetchone()[0]

        return count

    def get_user_list_met_logic_condition(self, institution_id, page, logic_condition_query_string,
                                          include_osf_user_query, logic_condition_params, include_osf_user_params):

        query = ''
        if len(logic_condition_query_string) > 0:
            query += f"""
                WITH userextendeddata AS (
                    SELECT DISTINCT user_id
                    FROM osf_userextendeddata
                    WHERE {logic_condition_query_string} )
            """

        query += """
            SELECT g._id AS guid, u.id, u.username, u.fullname, u.eppn
            FROM osf_osfuser AS u
            JOIN osf_guid AS g
                ON u.id = g.object_id
                AND g.content_type_id = 1
            JOIN osf_osfuser_affiliated_institutions AS ui
                ON u.id = ui.osfuser_id
            """
        if len(logic_condition_query_string) > 0:
            query += ' JOIN userextendeddata ux ON u.id = ux.user_id'
        query += """
            WHERE ui.institution_id = %s
                {}
                ORDER BY guid ASC
                LIMIT 10
                OFFSET (%s - 1) * 10
            """

        if len(include_osf_user_query) > 0:
            include_osf_user_query = f' AND {include_osf_user_query}'

        # Format the query with the logic condition
        formatted_query = query.format(include_osf_user_query)

        # Execute the raw query
        params = logic_condition_params + [institution_id] + include_osf_user_params + [page]
        with connection.cursor() as cursor:
            cursor.execute(formatted_query, params)
            user_list = cursor.fetchall()
            keys = ['guid', 'id', 'username', 'fullname', 'eppn']
            user_list = [dict(zip(keys, t)) for t in user_list]
        return user_list
