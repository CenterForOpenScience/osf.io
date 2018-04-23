# -*- coding: utf-8 -*-

from django.db import models
from osf.models.base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField, EncryptedTextField

class RdmAnnouncement(BaseModel):
    user = models.ForeignKey('OSFUser', null=True)
    title = models.CharField(max_length=256, blank=True, null=False)
    body = models.TextField(max_length=63206, null=False)
    announcement_type = models.CharField(max_length=256, null=False)
    date_sent = NonNaiveDateTimeField(auto_now_add=True)
    is_success = models.BooleanField(default=False)

class RdmAnnouncementOption(BaseModel):
    user = models.ForeignKey('OSFUser', null=True)
    twitter_api_key = EncryptedTextField(blank=True, null=True)
    twitter_api_secret = EncryptedTextField(blank=True, null=True)
    twitter_access_token = EncryptedTextField(blank=True, null=True)
    twitter_access_token_secret = EncryptedTextField(blank=True, null=True)
    facebook_api_key = EncryptedTextField(blank=True, null=True)
    facebook_api_secret = EncryptedTextField(blank=True, null=True)
    facebook_access_token = EncryptedTextField(blank=True, null=True)
    redmine_api_url = EncryptedTextField(blank=True, null=True)
    redmine_api_key = EncryptedTextField(blank=True, null=True)

class RdmFcmDevice(BaseModel):
    user = models.ForeignKey('OSFUser', null=True)
    device_token = EncryptedTextField(blank=True, null=True)
    date_created= NonNaiveDateTimeField(auto_now_add=True)
