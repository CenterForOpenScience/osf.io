# -*- coding: utf-8 -*-
from django.db import models

from osf.models.storage import StorageType


class ProjectStorageType(StorageType):
    node = models.OneToOneField('AbstractNode', on_delete=models.CASCADE)
    storage_type = models.IntegerField(
        choices=StorageType.STORAGE_TYPE_CHOICES,
        default=StorageType.NII_STORAGE)
