#
# MMAPProfile: Model handling OAuth2 tokens.
#
# @COPYRIGHT@
#
import datetime as dt
import logging

from django.db import models
from django.utils import timezone

from osf.models.base import BaseModel, GuidMixin, GuidMixinQuerySet
from osf.utils.fields import NonNaiveDateTimeField

logger = logging.getLogger(__name__)

class MAPProfile(BaseModel):
    oauth_access_token = models.CharField(null=True, blank=True, unique=True, max_length=255)
    oauth_refresh_token = models.CharField(null=True, blank=True, unique=True, max_length=255)
    oauth_refresh_time = NonNaiveDateTimeField(null=True, blank=True)
    #
    # Reference to OSFUser object.
    #
    #user = models.OneToOneField(OSFUser,
    #    null=False, related_name='map_user')

    def __unicode__(self):
        return self.oauth_access_token
