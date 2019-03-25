import datetime as dt
import logging

from django.db import models
from django.utils import timezone

from osf.models.base import BaseModel, GuidMixin, GuidMixinQuerySet
from osf.models.user import OSFUser
from osf.utils.fields import NonNaiveDateTimeField, LowercaseEmailField

logger = logging.getLogger(__name__)

class MAPProfile(BaseModel):
    oauth_access_token = models.CharField(blank=True, max_length=255, db_index=False, unique=True, null=True)
    oauth_refresh_token = models.CharField(blank=True, max_length=255, db_index=False, unique=True, null=True)
    oauth_refresh_time = NonNaiveDateTimeField(null=True, blank=True)
    # Reference to OSFUser
    user = models.OneToOneField(OSFUser,
        null = False, related_name = 'map_user')

    def __unicode__(self):
        return self.user.eppn

'''
class mApGroup(BaseModel):
    group_key = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    introduction = models.CharField(max_length=255, unique=False)
    is_active = models.BooleanField(db_index=True, default=False)
    is_public = models.BooleanField(db_index=True, default=False)
    is_inspect_join = models.BooleanField(db_index=True, default=False)
    is_open_member = models.PositiveIntegerField(db_index=True, default=False)

    def __unicode__(self):
        return self.name
'''
