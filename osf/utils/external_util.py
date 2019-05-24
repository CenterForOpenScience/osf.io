
# -*- coding: utf-8 -*-
from addons.osfstorage.models import Region
from osf.models.region_external_account import RegionExternalAccount
from osf.models.institution import Institution

def set_region_external_account(institution_id, account):
    institution_object = Institution.objects.get(pk=institution_id)
    region = Region.objects.filter(_id=institution_object._id).first()
    obj, created = RegionExternalAccount.objects.update_or_create(
        region=region,
        defaults={'external_account': account},
    )
