from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class RdmFileTimestamptokenVerifyResult(ObjectIDMixin, BaseModel):
    """A persistent identifier model for DOIs, ARKs, and the like."""

    # object to which the identifier points
    key_file_name = models.CharField(max_length=255)
    file_id = models.CharField(max_length=24)
    project_id = models.CharField(max_length=255)
    provider = models.CharField(max_length=25, null=True, blank=True)
    path = models.TextField(null=True, blank=True)
    timestamp_token = models.BinaryField(null=True, blank=True)
    inspection_result_status = models.IntegerField(default=0)
    create_user = models.IntegerField()
    create_date = models.DateTimeField()
    validation_user = models.IntegerField(null=True, blank=True)
    validation_date = models.DateTimeField(null=True, blank=True)
    update_user = models.IntegerField(null=True, blank=True)
    update_date = models.DateTimeField(null=True, blank=True)
