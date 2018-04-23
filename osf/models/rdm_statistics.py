# -*- coding: utf-8 -*-
"""model for rdm statistics"""

from django.db import models
from osf.models.base import BaseModel
from osf.models import AbstractNode, OSFUser, Institution


class RdmStatistics(BaseModel):
    """store statistics info of storage"""
    primary_identifier_name = 'id'
    project = models.ForeignKey(AbstractNode, blank=False, null=True)
    owner = models.ForeignKey(OSFUser, blank=False, null=True)
    institution = models.ForeignKey(Institution, blank=False, null=True)
    provider = models.CharField(max_length=50, blank=False, null=True, db_index=True)
    storage_account_id = models.CharField(max_length=256, null=True)
    project_root_path = models.CharField(max_length=256, null=False)
    extention_type = models.CharField(max_length=10, null=True)
    subtotal_file_number = models.BigIntegerField(null=False)
    subtotal_file_size = models.FloatField(null=False)
    date_acquired = models.DateField(null=False)

