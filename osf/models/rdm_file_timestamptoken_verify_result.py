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
    upload_file_created_user = models.IntegerField(null=True, blank=True)
    upload_file_created_at = models.DateTimeField(null=True, blank=True)
    upload_file_modified_user = models.IntegerField(null=True, blank=True)
    upload_file_modified_at = models.DateTimeField(null=True, blank=True)
    upload_file_size = models.IntegerField(null=True, blank=True)
    verify_user = models.IntegerField(null=True, blank=True)
    verify_date = models.DateTimeField(null=True, blank=True)
    verify_file_created_at = models.DateTimeField(null=True, blank=True)
    verify_file_modified_at = models.DateTimeField(null=True, blank=True)
    verify_file_size = models.IntegerField(null=True, blank=True)
