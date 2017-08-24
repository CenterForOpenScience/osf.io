# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from include import IncludeManager

from osf.models.base import ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField

from reviews.workflow import Actions
from reviews.workflow import States


class ReviewLog(ObjectIDMixin, models.Model):

    objects = IncludeManager()

    reviewable = models.ForeignKey('osf.PreprintService', related_name='review_logs')
    creator = models.ForeignKey('osf.OSFUser', related_name='+')

    action = models.CharField(max_length=31, choices=Actions.choices())
    from_state = models.CharField(max_length=31, choices=States.choices())
    to_state = models.CharField(max_length=31, choices=States.choices())

    comment = models.TextField(blank=True)

    is_deleted = models.BooleanField(default=False)
    date_created = NonNaiveDateTimeField(auto_now_add=True)
    date_modified = NonNaiveDateTimeField(auto_now=True)
