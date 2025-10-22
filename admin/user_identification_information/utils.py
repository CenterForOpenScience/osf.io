import logging
from django.db import connection

from api.base import settings as api_settings
from osf.models import ExternalAccount
from website.settings import ADDONS_FOLDER_FIELD

logger = logging.getLogger(__name__)


def custom_size_abbreviation(size, abbr):
    if abbr == 'B':
        return size / api_settings.BASE_FOR_METRIC_PREFIX, 'KB'
    return size, abbr


def get_list_extend_storage():
    external_accounts = ExternalAccount.objects.order_by('provider').values_list('provider', 'provider_name')
    dict_users_list = {}
    if len(external_accounts) == 0:
        return dict_users_list
    cursor = connection.cursor()

    # external_accounts in a list of tuple items
    for provider, provider_name in external_accounts:
        provider = provider.lower()

        # map from provider short-name to folder field-name (similar terminology: container/bucket/folder/repo/...)
        if provider not in ADDONS_FOLDER_FIELD:
            logger.warning(f'The folder field of "{provider}" provider has not been declared in addons.json')
            continue

        storage_branch_name = ADDONS_FOLDER_FIELD[provider]

        # query a list of (storage_branch_name, user_id)
        query_string = f"""
            select addons_{provider}_nodesettings.{storage_branch_name}, addons_{provider}_usersettings.owner_id as user_id
            from addons_{provider}_usersettings inner join addons_{provider}_nodesettings
            on addons_{provider}_nodesettings.user_settings_id = addons_{provider}_usersettings.id
            where addons_{provider}_usersettings.id in(
                select addons_{provider}_usersettings.id
                from osf_osfuser inner join addons_{provider}_usersettings
                on osf_osfuser.id = addons_{provider}_usersettings.owner_id)
            """
        cursor.execute(query_string)
        result = cursor.fetchall()

        # result in a list of tuple items
        if not result:
            continue

        for user_provider_name, user_id in result:
            name = '/'.join([user_provider_name or '', provider_name])
            if user_id not in dict_users_list:
                dict_users_list[user_id] = {name}
            else:
                dict_users_list[user_id].add(name)
    return dict_users_list
