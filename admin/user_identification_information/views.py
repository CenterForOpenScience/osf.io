from django.http import Http404
from django.views.generic import ListView

from admin.base.views import GuidView
from admin.rdm.utils import RdmPermissionMixin
from admin.user_identification_information.utils import (
    custom_size_abbreviation,
    get_list_extend_storage
)
from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota
from website.util import quota


class UserIdentificationInformationListView(ListView):

    def get_user_quota_info(self, user, storage_type, extend_storage=''):
        _, used_quota = quota.get_quota_info(user, storage_type)
        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))

        return {
            'id': user.guids.first()._id,
            'fullname': user.fullname,
            'eppn': user.eppn or '',
            'affiliation': user.affiliated_institutions.first() if user.affiliated_institutions.first() else '',
            'email': user.emails.values_list('address', flat=True)[0] if len(
                user.emails.values_list('address', flat=True)) > 0 else '',
            'last_login': user.last_login or '',
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'extended_storage': extend_storage,
        }

    def get_queryset(self):
        user_list = self.get_user_list()
        return user_list

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


class UserIdentificationListView(RdmPermissionMixin, UserIdentificationInformationListView):
    template_name = 'user_identification_information/list_user_identification.html'
    raise_exception = True
    paginate_by = 20

    def user_list(self):
        queryset = []
        if self.request.user.is_superuser is False:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None:
                queryset = OSFUser.objects.filter(affiliated_institutions=institution.id).order_by('id')
        else:
            queryset = OSFUser.objects.all().order_by('id')

        dict_users_list = get_list_extend_storage()
        return self.get_list_data(queryset, dict_users_list)

    def get_user_list(self):
        if self.is_admin or not self.is_authenticated:
            raise Http404('Page not found')
        return self.user_list()


class UserIdentificationDetailView(RdmPermissionMixin, GuidView):
    template_name = 'user_identification_information/user_identification_details.html'
    context_object_name = 'user_details'
    raise_exception = True

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
