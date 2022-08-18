import numpy as np
from django.db import connection

from api.base import settings as api_settings
from osf.models import ExternalAccount


def custom_size_abbreviation(size, abbr):
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
