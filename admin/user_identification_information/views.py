import numpy as np
from admin.base.views import GuidView
from api.base import settings as api_settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import connection
from django.views.generic import ListView
from osf.models import ExternalAccount
from osf.models import OSFUser, UserQuota
from website.util import quota


def custom_size_abbreviation(size, abbr, *kwargs):
    if abbr == 'B':
        return (size / api_settings.BASE_FOR_METRIC_PREFIX, 'KB')
    return size, abbr


def get_list_extend_storage():
    values = ExternalAccount.objects.values_list('provider', 'provider_name')
    get_provider, get_provider_name = map(list, zip(*values))
    dict_users_list = {}
    storage_branch_name = None
    cursor = connection.cursor()

    for j in range(len(get_provider)):
        provider_value = get_provider[j]
        get_provider_name_value = get_provider_name[j]
        if any(s in provider_value.lower() for s in
               ('s3', 's3compat', 's3compatb3', 'azureblobstorage', 'box',
                'figshare', 'onedrivebusiness', 'swift')):
            storage_branch_name = 'folder_name'
        elif any(s in provider_value.lower() for s in ('bitbucket', 'github',
                                                       'gitlab')):
            storage_branch_name = 'repo'
        elif any(s in provider_value.lower() for s in ('googledrive',
                                                       'onedrive', 'iqbrims')):
            storage_branch_name = 'folder_path'
        elif any(s in provider_value.lower() for s in ('dropbox')):
            storage_branch_name = 'folder'
        elif any(s in provider_value.lower() for s in ('weko')):
            storage_branch_name = 'index_title'
        elif any(s in provider_value.lower() for s in ('mendeley', 'zotero')):
            storage_branch_name = 'list_id'
        elif any(s in provider_value.lower() for s in ('owncloud')):
            storage_branch_name = 'folder_id'
        elif any(s in provider_value.lower() for s in ('dataverse')):
            storage_branch_name = 'dataverse'

        cursor.execute(
            """
            select addons_%s_nodesettings.%s, addons_%s_usersettings.owner_id as user_id
            from addons_%s_usersettings inner join addons_%s_nodesettings
            on addons_%s_nodesettings.user_settings_id = addons_%s_usersettings.id
            where addons_%s_usersettings.id in(
                select addons_%s_usersettings.id from osf_osfuser inner join addons_%s_usersettings
                on osf_osfuser.id = addons_%s_usersettings.owner_id)
            """ % (
                provider_value, storage_branch_name, provider_value, provider_value, provider_value, provider_value,
                provider_value, provider_value, provider_value, provider_value, provider_value)
        )
        result = np.asarray(cursor.fetchall())
        list_users_provider = result[:, 0]
        list_users_id = result[:, 1]

        for i in range(len(list_users_id)):
            if list_users_id[i] not in dict_users_list:
                dict_users_list[list_users_id[i]] = [
                    list_users_provider[i] + '/' +
                    get_provider_name_value if list_users_provider[i] is not None else '/' + get_provider_name_value]
            else:
                current_val = dict_users_list.get(list_users_id[i])
                current_val.append(
                    list_users_provider[i] + '/' +
                    get_provider_name_value if list_users_provider[i] is not None else '/' + get_provider_name_value)
                dict_users_list[list_users_id[i]] = current_val
        return list_users_id, dict_users_list


class UserIdentificationInformation(ListView):

    def get_user_quota_info(self, user, storage_type, extend_storage=''):
        _, used_quota = quota.get_quota_info(user, storage_type)
        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))

        return {
            'id': user.guids.first()._id,
            'fullname': user.fullname,
            'eppn': user.eppn or '',
            'affiliation': user.affiliated_institutions.first(),
            'email': user.emails.values_list('address', flat=True)[0] if len(
                user.emails.values_list('address', flat=True)) > 0 else '',
            'last_login': user.last_login or '',
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'extended_storage': extend_storage,

        }

    def get_queryset(self):
        user_list = self.get_userlist()
        return user_list

    def get_context_data(self, **kwargs):
        self.query_set = self.get_userlist()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['requested_user'] = self.request.user
        kwargs['institution_name'] = self.request.user.affiliated_institutions.first().name \
            if self.request.user.is_superuser is False else None
        kwargs['users'] = self.query_set
        kwargs['page'] = self.page
        return super(UserIdentificationInformation, self).get_context_data(**kwargs)

    def get_list_data(self, queryset, list_users_id=[], dict_users_list={}):
        list_data = []
        for user in queryset:
            if user.id in list_users_id:
                list_data.append(
                    self.get_user_quota_info(user, UserQuota.NII_STORAGE, '\n'.join(dict_users_list.get(user.id))))
            else:
                list_data.append(self.get_user_quota_info(user, UserQuota.NII_STORAGE))
        return list_data


class UserIdentificationList(PermissionRequiredMixin, UserIdentificationInformation):
    template_name = 'user_identification_information/list_user_identification.html'
    permission_required = ''
    raise_exception = True
    paginate_by = 20

    def get_userlist(self):
        queryset = []
        if self.request.user.is_superuser is False:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None:  # and Region.objects.filter(_id=institution._id).exists():
                queryset = OSFUser.objects.filter(affiliated_institutions=institution.id).order_by('id')
        else:
            queryset = OSFUser.objects.all().order_by('id')

        list_users_id, dict_users_list = get_list_extend_storage()

        return self.get_list_data(queryset, list_users_id, dict_users_list)


class UserIdentificationDetails(PermissionRequiredMixin, GuidView):
    template_name = 'user_identification_information/user_identification_details.html'
    context_object_name = 'user_details'
    permission_required = ''
    raise_exception = True

    def get_object(self):
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
