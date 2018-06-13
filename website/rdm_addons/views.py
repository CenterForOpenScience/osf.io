# -*- coding: utf-8 -*-

import httplib

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from addons.base import utils as addon_utils
from admin.rdm_addons import utils as rdm_addons_utils
from admin.rdm import utils as rdm_utils

@must_be_logged_in
def user_addons(auth):
    user = auth.user

    addon_settings = addon_utils.get_addons_by_config_type('accounts', user)
    # RDM
    rdm_addons_utils.update_with_rdm_addon_settings(addon_settings, user)

    ret = {}
    for addon in addon_settings:
        ret[addon['addon_short_name']] = {
            'is_allowed': addon['is_allowed'],
            'is_forced': addon['is_forced'],
            'is_enabled': addon['is_enabled'],
            'has_external_accounts': addon['has_external_accounts'],
            'addon_short_name': addon['addon_short_name'],
        }

    return ret

@must_be_logged_in
def import_admin_account(auth, addon_name=None):
    user = auth.user

    institution_id = rdm_utils.get_institution_id(user)
    rdm_addon_option = rdm_addons_utils.get_rdm_addon_option(institution_id, addon_name)

    if not rdm_addon_option.external_accounts.exists():
        raise HTTPError(httplib.BAD_REQUEST)

    for account in rdm_addon_option.external_accounts.all():
        user.external_accounts.add(account)

    user.get_or_add_addon(addon_name, auth=auth)
    user.save()
    return {}
