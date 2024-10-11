import csv
from operator import itemgetter

import pytz
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponse
from django.views.generic import ListView

from admin.base.views import GuidView
from admin.rdm.utils import RdmPermissionMixin
from admin.user_identification_information.utils import (
    custom_size_abbreviation,
    get_list_extend_storage
)
from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota, Email
from website.util import quota
from datetime import datetime
from django.contrib.auth.mixins import UserPassesTestMixin


class UserIdentificationInformationListView(ListView):

    def get_user_quota_info(self, user, storage_type, extend_storage=''):
        _, used_quota = quota.get_quota_info(user, storage_type)
        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))

        return {
            'id': user.guids.first()._id,
            'fullname': user.fullname,
            'eppn': user.eppn or '',
            'affiliation': user.affiliated_institutions.first().name if user.affiliated_institutions.first() else '',
            'email': user.emails.values_list('address', flat=True)[0] if len(
                user.emails.values_list('address', flat=True)) > 0 else '',
            'last_login': user.last_login or pytz.utc.localize(datetime.min),
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'extended_storage': extend_storage,
        }

    def get_queryset(self):
        user_list = self.get_user_list()
        order_by = self.get_order_by()
        reverse = self.get_direction() != 'asc'
        user_list.sort(key=itemgetter(order_by), reverse=reverse)
        return user_list

    def get_order_by(self):
        order_by = self.request.GET.get('order_by', 'usage')
        if order_by not in ['fullname', 'eppn', 'last_login', 'usage', 'affiliation', 'email', 'extended_storage']:
            return 'usage'
        return order_by

    def get_direction(self):
        direction = self.request.GET.get('status', 'desc')
        if direction not in ['asc', 'desc']:
            return 'desc'
        return direction

    def get_context_data(self, **kwargs):
        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['requested_user'] = self.request.user
        kwargs['institution_name'] = self.request.user.affiliated_institutions.first().name \
            if self.request.user.is_superuser is False else None
        kwargs['users'] = self.query_set
        kwargs['page'] = self.page
        kwargs['order_by'] = self.get_order_by()
        kwargs['direction'] = self.get_direction()
        kwargs['datetime_min'] = pytz.utc.localize(datetime.min)
        kwargs['guid'] = self.request.GET.get('guid') or ''
        kwargs['fullname'] = self.request.GET.get('fullname') or ''
        kwargs['username'] = self.request.GET.get('username') or ''
        return super(UserIdentificationInformationListView, self).get_context_data(**kwargs)

    def get_list_data(self, queryset, dict_users_list={}):
        list_data = []
        for user in queryset:
            if user.id in dict_users_list:
                list_data.append(
                    self.get_user_quota_info(user, UserQuota.NII_STORAGE, '\n'.join(dict_users_list.get(user.id))))
            else:
                list_data.append(self.get_user_quota_info(user, UserQuota.NII_STORAGE))
        return list_data


class UserIdentificationListView(RdmPermissionMixin, UserPassesTestMixin, UserIdentificationInformationListView):
    template_name = 'user_identification_information/list_user_identification.html'
    raise_exception = True
    paginate_by = 20

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if superuser
        return self.is_super_admin

    def user_list(self):
        guid = self.request.GET.get('guid')
        name = self.request.GET.get('fullname')
        email = self.request.GET.get('username')
        queryset = []
        if self.request.user.is_superuser is False:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None:
                queryset = OSFUser.objects.filter(affiliated_institutions=institution.id).order_by('id')
        else:
            queryset = OSFUser.objects.all().order_by('id')

        dict_users_list = get_list_extend_storage()

        if not email and not guid and not name:
            return self.get_list_data(queryset, dict_users_list)

        query_email = query_guid = query_name = None
        if email:
            existing_user_ids = list(Email.objects.filter(Q(address__exact=email)).values_list('user_id', flat=True))
            query_email = queryset.filter(Q(pk__in=existing_user_ids) | Q(username__exact=email))
        if guid:
            query_guid = queryset.filter(guids___id=guid)
        if name:
            query_name = queryset.filter(Q(fullname__icontains=name) |
                                         Q(family_name_ja__icontains=name) |
                                         Q(given_name_ja__icontains=name) |
                                         Q(middle_names_ja__icontains=name) |
                                         Q(given_name__icontains=name) |
                                         Q(middle_names__icontains=name) |
                                         Q(family_name__icontains=name))

        if query_email is not None and query_email.exists():
            return self.get_list_data(query_email, dict_users_list)
        elif query_guid is not None and query_guid.exists():
            return self.get_list_data(query_guid, dict_users_list)
        elif query_name is not None and query_name.exists():
            return self.get_list_data(query_name, dict_users_list)
        else:
            return []

    def get_user_list(self):
        if self.is_admin or not self.is_authenticated:
            raise Http404('Page not found')
        return self.user_list()


class UserIdentificationDetailView(RdmPermissionMixin, UserPassesTestMixin, GuidView):
    template_name = 'user_identification_information/user_identification_details.html'
    context_object_name = 'user_details'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if superuser
        return self.is_super_admin

    def user_details(self):
        user_details = OSFUser.load(self.kwargs.get('guid'))
        user_id = int(user_details.id)
        max_quota, used_quota = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)
        max_quota_bytes = max_quota * api_settings.SIZE_UNIT_GB
        remaining_quota = max_quota_bytes - used_quota

        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))
        remaining_abbr = custom_size_abbreviation(*quota.abbreviate_size(remaining_quota))
        max_quota, _ = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)

        dict_users_list = get_list_extend_storage()
        extend_storage = ''
        if user_id in dict_users_list:
            extend_storage = '\n'.join(dict_users_list.get(user_id))

        return {
            'username': user_details.username,
            'name': user_details.fullname,
            'id': user_details._id,
            'emails': user_details.emails.values_list('address', flat=True),
            'last_login': user_details.last_login,
            'confirmed': user_details.date_confirmed,
            'registered': user_details.date_registered,
            'disabled': user_details.date_disabled if user_details.is_disabled else False,
            'two_factor': user_details.has_addon('twofactor'),
            'osf_link': user_details.absolute_url,
            'system_tags': user_details.system_tags or '',
            'quota': max_quota,
            'affiliation': user_details.affiliated_institutions.first() or '',
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'remaining': remaining_quota,
            'remaining_value': remaining_abbr[0],
            'remaining_abbr': remaining_abbr[1],
            'extended_storage': extend_storage,
        }

    def get_object(self):
        if self.is_admin or not self.is_authenticated:
            raise Http404('Page not found')
        return self.user_details()


class ExportFileCSVView(RdmPermissionMixin, UserPassesTestMixin, UserIdentificationInformationListView):
    """Response a CSV file in name format:
    - for super admin: export_user_identification_{institution_guid}_{yyyymmddhhMMSS}.csv
    - for admin: filename=export_user_identification_{yyyymmddhhMMSS}.csv
    """
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if superuser
        return self.is_super_admin

    def get(self, request, **kwargs):
        time_now = datetime.today().strftime('%Y%m%d%H%M%S')
        response = HttpResponse(content_type='text/csv')
        if self.is_super_admin:
            response['Content-Disposition'] = f'attachment;filename=export_user_identification_{time_now}.csv'
        else:
            institution = self.request.user.affiliated_institutions.first()._id
            if institution is not None:
                response['Content-Disposition'] = f'attachment;filename=export_user_identification_{institution}_{time_now}.csv'

        writer = csv.writer(response)
        writer.writerow(
            ['GUID', 'EPPN', 'Fullname', 'Email', 'Affiliation', 'Last login', 'Usage (Byte)', 'Extended storage'])
        queryset = []

        if self.request.user.is_superuser is False:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None:
                queryset = OSFUser.objects.filter(affiliated_institutions=institution.id).order_by('id')
        else:
            queryset = OSFUser.objects.all().order_by('id')

        dict_users_list = get_list_extend_storage()
        for user in queryset:
            extend_storage = ''
            max_quota, used_quota = quota.get_quota_info(user, UserQuota.NII_STORAGE)
            if user.id in dict_users_list:
                extend_storage = '\n'.join(dict_users_list.get(user.id))
            writer.writerow([user.guids.first()._id,
                             user.eppn,
                             user.fullname,
                             user.emails.values_list('address', flat=True)[0] if len(user.emails.values_list('address', flat=True)) > 0 else '',
                             user.affiliated_institutions.first().name if user.affiliated_institutions.first() else '',
                             user.last_login,
                             used_quota,
                             extend_storage])
        return response
