# -*- coding: utf-8 -*-

def serialize_account(account):
    if account is None:
        return None
    return {
        'id': account._id,
        'provider_id': account.provider_id,
        'display_name': account.display_name,
    }
