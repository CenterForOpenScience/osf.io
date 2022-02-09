import logging
from django.core.cache import cache

from framework.exceptions import HTTPError
from osf.models import RdmAddonOption
from osf.models.region_external_account import RegionExternalAccount
from addons.osfstorage.models import Region
from addons.onedrivebusiness import SHORT_NAME

from addons.onedrivebusiness.client import UserListClient
from addons.onedrivebusiness import settings


logger = logging.getLogger(__name__)


def parse_root_folder_id(root_folder_id):
    if '\t' not in root_folder_id:
        return None, root_folder_id
    return tuple(root_folder_id.split('\t', maxsplit=1))

def get_region_external_account(node):
    user = node.creator
    if user is None:
        return None
    institution = user.affiliated_institutions.first()
    if institution is None:
        return None
    addon_option = RdmAddonOption.objects.filter(
        provider=SHORT_NAME,
        institution_id=institution.id,
        is_allowed=True
    ).first()
    if addon_option is None:
        return None
    try:
        region = Region.objects.get(_id=institution._id)
        return RegionExternalAccount.objects.get(region=region)
    except Region.DoesNotExist:
        return None

def get_column_id(sheet, text):
    for row in sheet.iter_rows():
        for cell in list(row):
            if str(cell.value).strip() == text:
                return (cell.column_letter, cell.row)
    raise KeyError('Column "{}" is not found in userlist'.format(text))

def get_sheet_values(sheet, column_ids):
    start_row = max([row for _, row in column_ids]) + 1
    values = []
    for row in sheet.iter_rows(min_row=start_row):
        v = []
        logger.debug('Row: {}'.format(row))
        for col, _ in column_ids:
            target = None
            for cell in list(row):
                if str(cell.value).startswith('#'):
                    continue
                if cell.column_letter == col:
                    target = cell.value
            v.append(target)
        if any([e is None for e in v]):
            continue
        values.append(v)
    return values

def get_user_item(region_client, folder_id, values):
    eppn, msaccount = values
    user_info = cache.get('{}:{}'.format(folder_id, msaccount))
    if user_info is not None:
        return (eppn, user_info)
    try:
        user = region_client.get_user(msaccount)
        logger.debug('User: {}'.format(user))
        user_info = {'userPrincipalName': msaccount, 'id': user['id'], 'mail': user['mail']}
        cache.set('{}:{}'.format(folder_id, msaccount), user_info, settings.TEAM_MEMBER_USER_CACHE_TIMEOUT)
        return (eppn, user_info)
    except HTTPError:
        logger.warning('Cannot get user details for {}'.format(msaccount))
    return (eppn, {'userPrincipalName': msaccount, 'id': None})

def get_user_map(region_client, folder_id, filename=None, sheet_name=None):
    user_map = cache.get(folder_id)
    if user_map is not None:
        return user_map
    client = UserListClient(region_client, folder_id,
                            filename=filename, sheet_name=sheet_name)
    sheet = client.get_workbook_sheet()
    column_texts = ['ePPN', 'MicrosoftAccount']
    column_ids = [get_column_id(sheet, text) for text in column_texts]
    logger.debug('column_ids: {}'.format(column_ids))
    user_map = dict([get_user_item(region_client, folder_id, v)
                     for v in get_sheet_values(sheet, column_ids)])
    cache.set(folder_id, user_map, settings.TEAM_MEMBER_LIST_CACHE_TIMEOUT)
    return user_map
