# -*- coding: utf-8 -*-

def serialize_account(account):
    if account is None:
        return None
    return {
        'id': account._id,
        'provider_id': account.provider_id,
        'display_name': account.display_name,
    }

def serialize_folder(name, parent_id=None, list_id=None, id=None):
    retval = {
        'name': name,
        'provider_list_id': list_id,
        'id': id
    }
    if parent_id:
        retval['parent_list_id'] = parent_id

    return retval
