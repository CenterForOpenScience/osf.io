# -*- coding: utf-8 -*-

from django.db import models
from osf.models.base import BaseModel
from osf.models import Institution


class RdmTimestampGrantPattern(BaseModel):

    institution = models.ForeignKey(Institution, blank=False, null=True)
    node_guid = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    timestamp_pattern_division = models.IntegerField(default=1)
    is_forced = models.BooleanField(default=False)

    class Meta:
        unique_together = (('institution', 'node_guid'))
