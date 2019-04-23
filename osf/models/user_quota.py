# -*- coding: utf-8 -*-
from django.db import models

from osf.models.base import BaseModel


class UserQuota(BaseModel):
    NII_STORAGE = 1
    CUSTOM_STORAGE = 2

    STORAGE_TYPE_CHOICES = (
        (NII_STORAGE, 'NII Storage'),
        (CUSTOM_STORAGE, 'Custom Storage'),
    )

    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    storage_type = models.IntegerField(choices=STORAGE_TYPE_CHOICES, default=NII_STORAGE)
    max_quota = models.IntegerField(default=100)
    used = models.BigIntegerField(default=0)
