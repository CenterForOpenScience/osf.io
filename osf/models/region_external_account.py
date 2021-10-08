# -*- coding: utf-8 -*-
from django.db import models

from osf.models.base import BaseModel
from addons.osfstorage.models import Region


class RegionExternalAccount(BaseModel):
    external_account = models.ForeignKey('ExternalAccount', on_delete=models.CASCADE, null=False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=False)
