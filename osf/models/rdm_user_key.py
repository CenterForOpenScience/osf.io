from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class RdmUserKey(ObjectIDMixin, BaseModel):
    """A persistent identifier model for DOIs, ARKs, and the like."""

    # object to which the identifier points
    guid = models.IntegerField()
    key_name = models.CharField(max_length=50)
    key_kind = models.IntegerField()
    created_time = models.DateTimeField()
    delete_flag = models.IntegerField(default=0)
