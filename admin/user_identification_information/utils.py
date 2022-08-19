import numpy as np
from django.db import connection

from api.base import settings as api_settings
from osf.models import ExternalAccount


def custom_size_abbreviation(size, abbr):
    if abbr == 'B':
        return size / api_settings.BASE_FOR_METRIC_PREFIX, 'KB'
    return size, abbr


def get_list_extend_storage():
    values = ExternalAccount.objects.values_list('provider', 'provider_name')
    provider_list, provider_name_list = map(list, zip(*values))
    dict_users_list = {}
    storage_branch_name = None
    cursor = connection.cursor()

    for index in range(len(provider_list)):
        provider = provider_list[index]
        provider_name = provider_name_list[index]
        if any(s in provider.lower() for s in
               ('s3', 's3compat', 's3compatb3', 'azureblobstorage', 'box', 'figshare', 'onedrivebusiness', 'swift',)):
            storage_branch_name = 'folder_name'
        elif any(s in provider.lower() for s in ('bitbucket', 'github', 'gitlab',)):
            storage_branch_name = 'repo'
        elif any(s in provider.lower() for s in ('googledrive', 'onedrive', 'iqbrims',)):
            storage_branch_name = 'folder_path'
        elif any(s in provider.lower() for s in ('dropbox',)):
            storage_branch_name = 'folder'
        elif any(s in provider.lower() for s in ('weko',)):
            storage_branch_name = 'index_title'
        elif any(s in provider.lower() for s in ('mendeley', 'zotero',)):
            storage_branch_name = 'list_id'
        elif any(s in provider.lower() for s in ('owncloud',)):
            storage_branch_name = 'folder_id'
        elif any(s in provider.lower() for s in ('dataverse',)):
            storage_branch_name = 'dataverse'

        query_string = """
            select addons_{provider}_nodesettings.{storage_branch_name}, addons_{provider}_usersettings.owner_id as user_id
            from addons_{provider}_usersettings inner join addons_{provider}_nodesettings
            on addons_{provider}_nodesettings.user_settings_id = addons_{provider}_usersettings.id
            where addons_{provider}_usersettings.id in(
                select addons_{provider}_usersettings.id from osf_osfuser inner join addons_{provider}_usersettings
                on osf_osfuser.id = addons_{provider}_usersettings.owner_id)
            """.format(provider=provider, storage_branch_name=storage_branch_name)
        cursor.execute(query_string)
        result = np.asarray(cursor.fetchall())
        list_users_provider = result[:, 0]
        list_users_id = list(map(int, result[:, 1]))

        for idx in range(len(list_users_id)):
            if list_users_id[idx] not in dict_users_list:
                dict_users_list[list_users_id[idx]] = [
                    list_users_provider[idx] + '/' +
                    provider_name if list_users_provider[idx] is not None else '/' + provider_name]
            else:
                current_val = dict_users_list.get(list_users_id[idx])
                current_val.append(
                    list_users_provider[idx] + '/' +
                    provider_name if list_users_provider[idx] is not None else '/' + provider_name)
                dict_users_list[list_users_id[idx]] = current_val
    return dict_users_list
