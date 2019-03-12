# -*- coding: utf-8 -*-
from django.db import models

from osf.models.base import BaseModel


class UserQuota(BaseModel):
    user = models.OneToOneField('OSFUser', on_delete=models.CASCADE)
    max_quota = models.IntegerField(default=100)
