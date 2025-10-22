# -*- coding: utf-8 -*-
from django.db import models

from osf.models.storage import StorageType


class UserQuota(StorageType):
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    storage_type = models.IntegerField(
        choices=StorageType.STORAGE_TYPE_CHOICES,
        default=StorageType.NII_STORAGE)
    max_quota = models.IntegerField(default=100)
    used = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ['user', 'storage_type']
