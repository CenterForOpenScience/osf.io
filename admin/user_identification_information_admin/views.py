from django.http import Http404
from django.views.generic import ListView

from admin.base.views import GuidView
from admin.rdm.utils import RdmPermissionMixin
from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota
from osf.models.files import BaseFileNode
from website.util import quota


def custom_size_abbreviation(size, abbr, *kwargs):
    if abbr == 'B':
        return (size / api_settings.BASE_FOR_METRIC_PREFIX, 'KB')
    return size, abbr


def check_extended_storage(user):
    check_provider = set(BaseFileNode.objects.filter(checkout_id=user.id).values_list('provider', flat=True))
    return True if len(check_provider) > 1 else False


class UserIdentificationInformation(ListView):

    def get_user_quota_info(self, user, storage_type):
        _, used_quota = quota.get_quota_info(user, storage_type)
        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))

        return {
            'id': user.guids.first()._id,
            'fullname': user.fullname,
            'eppn': user.eppn or '',
            'affiliation': user.affiliated_institutions.first(),
            'email': user.emails.values_list('address', flat=True)[0] or '',
            'last_login': user.last_login or '',
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'extended_storage': check_extended_storage(user),
        }

    def get_queryset(self):
        user_list = self.get_userlist()
        return user_list

    def get_context_data(self, **kwargs):
        if self.request.user.is_superuser:
            raise Http404("Page not found")

        self.query_set = self.get_userlist()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['requested_user'] = self.request.user
        kwargs['institution_name'] = self.request.user.affiliated_institutions.first()
        kwargs['users'] = self.query_set
        kwargs['page'] = self.page
        return super(UserIdentificationInformation, self).get_context_data(**kwargs)


class UserIdentificationList(RdmPermissionMixin, UserIdentificationInformation):
    template_name = 'user_identification_information/list_user_identification.html'
    permission_required = ''
    raise_exception = True
    paginate_by = 20

    def get_userlist(self):
        queryset = []
        institution = self.request.user.affiliated_institutions.first()
        if institution is not None:  # and Region.objects.filter(_id=institution._id).exists():
            queryset = OSFUser.objects.filter(affiliated_institutions=institution.id)
        return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in queryset]


class UserIdentificationDetails(RdmPermissionMixin, GuidView):
    template_name = 'user_identification_information/user_identification_details.html'
    context_object_name = 'user_details'
    permission_required = ''
    raise_exception = True

    def get_object(self):
        if self.request.user.is_superuser:
            raise Http404("Page not found")

        user_details = OSFUser.load(self.kwargs.get('guid'))
        max_quota, used_quota = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)
        max_quota_bytes = max_quota * api_settings.SIZE_UNIT_GB
        remaining_quota = max_quota_bytes - used_quota

        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))
        remaining_abbr = custom_size_abbreviation(*quota.abbreviate_size(remaining_quota))
        max_quota, _ = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)

        return {
            'username': user_details.username,
            'name': user_details.fullname,
            'id': user_details._id,
            'emails': user_details.emails.values_list('address', flat=True),
            'last_login': user_details.date_last_login,
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
            'extended_storage': check_extended_storage(user_details),
        }
