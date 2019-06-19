
# -*- coding: utf-8 -*-
from addons.osfstorage.models import Region
from osf.models.region_external_account import RegionExternalAccount
from osf.models.institution import Institution
from osf.models.external import ExternalAccount


def set_region_external_account(institution_id, account):
    institution_object = Institution.objects.get(pk=institution_id)
    region = Region.objects.filter(_id=institution_object._id).first()
    obj, created = RegionExternalAccount.objects.update_or_create(
        region=region,
        defaults={
            'external_account': account,
            'region': region,
        },
    )
    set_new_access_token(region.id, get_oauth_key_by_external_id(account.id))

def set_new_access_token(region_id, access_token):
    region = Region.objects.get(pk=region_id)
    region.waterbutler_credentials['storage']['token'] = access_token
    region.save()

def get_oauth_key_by_external_id(external_account_id):
    return ExternalAccount.objects.get(pk=external_account_id).oauth_key

def is_custom_googledrive(external_account_id):
    return RegionExternalAccount.objects.filter(external_account_id=external_account_id).exists()

def get_region_id_by_external_id(external_account_id):
    return RegionExternalAccount.objects.get(external_account_id__exact=external_account_id).region_id
