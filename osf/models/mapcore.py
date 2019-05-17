#
# MAPProfile: Model handling OAuth2 tokens.
#
# @COPYRIGHT@
#
import logging

from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField

logger = logging.getLogger(__name__)

class MAPProfile(BaseModel):
    oauth_access_token = models.CharField(null=True, blank=True, max_length=255)
    oauth_refresh_token = models.CharField(null=True, blank=True, max_length=255)
    oauth_refresh_time = NonNaiveDateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.oauth_access_token
