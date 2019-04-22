# -*- coding: utf-8 -*-
from django.db import models

from osf.models.base import BaseModel


class ProjectStorageType(BaseModel):
    NII_STORAGE = 1
    CUSTOM_STORAGE = 2

    STORAGE_TYPE_CHOICES = (
        (NII_STORAGE, 'NII Storage'),
        (CUSTOM_STORAGE, 'Custom Storage'),
    )

    node = models.OneToOneField('AbstractNode', on_delete=models.CASCADE)
    storage_type = models.IntegerField(choices=STORAGE_TYPE_CHOICES, default=NII_STORAGE)
