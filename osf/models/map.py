import datetime as dt
import logging
#import re
#import urllib
#import urlparse
#import uuid
#from copy import deepcopy
#from os.path import splitext

#from flask import Request as FlaskRequest
#from framework import analytics
#from guardian.shortcuts import get_perms

# OSF imports
#import itsdangerous
#import pytz
#from dirtyfields import DirtyFieldsMixin

#from django.conf import settings
#from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
#from django.contrib.auth.hashers import check_password
#from django.contrib.auth.models import PermissionsMixin
#from django.dispatch import receiver
from django.db import models
#from django.db.models import Count
#from django.db.models.signals import post_save
from django.utils import timezone

#from framework.auth import Auth, signals, utils
#from framework.auth.core import generate_verification_key
'''
from framework.auth.exceptions import (ChangePasswordError, ExpiredTokenError,
                                       InvalidTokenError,
                                       MergeConfirmedRequiredError,
                                       MergeConflictError)
'''
#from framework.exceptions import PermissionsError
#from framework.sessions.utils import remove_sessions_for_user
#from osf.utils.requests import get_current_request
#from osf.exceptions import reraise_django_validation_errors, MaxRetriesError, UserStateError
from osf.models.base import BaseModel, GuidMixin, GuidMixinQuerySet
#from osf.models.contributor import Contributor, RecentlyAddedContributor
#from osf.models.institution import Institution
#from osf.models.mixins import AddonModelMixin
#from osf.models.session import Session
#from osf.models.tag import Tag
#from osf.models.validators import validate_email, validate_social, validate_history_item
from osf.models.user import OSFUser
#from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField, LowercaseEmailField
#from osf.utils.names import impute_names
#from osf.utils.requests import check_select_for_update
#from website import settings as website_settings
#from website import filters, mails
#from website.project import new_bookmark_collection

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
