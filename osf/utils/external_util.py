# -*- coding: utf-8 -*-
from addons.osfstorage.models import Region
from osf.models.region_external_account import RegionExternalAccount


def set_region_external_account(institution_id, account):
    region = Region.objects.get(_id=institution_id)
    RegionExternalAccount.objects.create(
        region=region,
        external_account=account,
    )
    set_new_access_token(account, region)

def set_new_access_token(external_account, region=None):
    if region is None:
        region = RegionExternalAccount.objects.get(external_account=external_account).region
    region.waterbutler_credentials['storage']['token'] = external_account.oauth_key
    region.save()

def is_institutional_storage(external_account):
    return RegionExternalAccount.objects.filter(external_account=external_account).exists()
