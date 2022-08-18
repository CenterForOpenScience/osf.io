from django.db.models import Q
from django.http import Http404

from admin.user_identification_information.views import (
    UserIdentificationInformation as UserIdentificationInformationBaseClass,
    UserIdentificationList as UserIdentificationListBaseClass,
    UserIdentificationDetails as UserIdentificationDetailsBaseClass,
    ExportFileCSV as ExportFileCSVBaseClass,
    custom_size_abbreviation,
    get_list_extend_storage,
)
from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota, Email
from website.util import quota


class UserIdentificationInformation(UserIdentificationInformationBaseClass):

    def get_context_data(self, **kwargs):
        if self.is_super_admin:
            raise Http404('Page not found')
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
        return super(UserIdentificationInformation, self).get_context_data(**kwargs)


class UserIdentificationList(UserIdentificationListBaseClass):

    def get_userlist(self):
        if self.is_super_admin:
            raise Http404('Page not found')
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

        list_users_id, dict_users_list = get_list_extend_storage()

        if not email and not guid and not name:
            return self.get_list_data(queryset, list_users_id, dict_users_list)

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
            return self.get_list_data(query_email, list_users_id, dict_users_list)
        elif query_guid is not None and query_guid.exists():
            return self.get_list_data(query_guid, list_users_id, dict_users_list)
        elif query_name is not None and query_name.exists():
            return self.get_list_data(query_name, list_users_id, dict_users_list)
        else:
            return []


class UserIdentificationDetails(UserIdentificationDetailsBaseClass):

    def get_object(self):
        if self.is_super_admin:
            raise Http404('Page not found')
        user_details = OSFUser.load(self.kwargs.get('guid'))
        user_id = int(user_details.id)
        max_quota, used_quota = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)
        max_quota_bytes = max_quota * api_settings.SIZE_UNIT_GB
        remaining_quota = max_quota_bytes - used_quota

        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))
        remaining_abbr = custom_size_abbreviation(*quota.abbreviate_size(remaining_quota))
        max_quota, _ = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)

        list_users_id, dict_users_list = get_list_extend_storage()
        extend_storage = ''
        if user_id in list_users_id:
            extend_storage = '\n'.join(dict_users_list.get(user_id))

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
            'extended_storage': extend_storage,
        }


class ExportFileCSV(ExportFileCSVBaseClass):
    pass
