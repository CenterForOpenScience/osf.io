import logging

from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField

logger = logging.getLogger(__name__)

#
# MAPSync: Status of synchronization
#
class MAPSync(BaseModel):
    VERSION = 1

    version = models.IntegerField(unique=True)
    enabled = models.BooleanField(default=True)

    @classmethod
    def is_enabled(cls):
        map_sync, created = cls.objects.get_or_create(version=cls.VERSION)
        return map_sync.enabled

    @classmethod
    def set_enabled(cls, b):
        map_sync, created = cls.objects.get_or_create(version=cls.VERSION)
        map_sync.enabled = b
        map_sync.save()


#
# MAPProfile: OAuth2 tokens for users.
#
class MAPProfile(BaseModel):
    oauth_access_token = models.CharField(null=True, blank=True, max_length=255)
    oauth_refresh_token = models.CharField(null=True, blank=True, max_length=255)
    oauth_refresh_time = NonNaiveDateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.oauth_access_token
