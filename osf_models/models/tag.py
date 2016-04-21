from django.db import models

from .base import BaseModel


class Tag(BaseModel):
    _id = models.CharField(max_length=1024, db_index=True)
    lower = models.CharField(max_length=1024, db_index=True)
    system = models.BooleanField(default=False)
