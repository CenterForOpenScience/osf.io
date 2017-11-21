# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from include import IncludeManager

from reviews.workflow import Triggers
from reviews.workflow import States

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField


class Action(ObjectIDMixin, BaseModel):

    objects = IncludeManager()

    target = models.ForeignKey('PreprintService', related_name='actions', on_delete=models.CASCADE)
    creator = models.ForeignKey('OSFUser', related_name='+', on_delete=models.CASCADE)

    trigger = models.CharField(max_length=31, choices=Triggers.choices())
    from_state = models.CharField(max_length=31, choices=States.choices())
    to_state = models.CharField(max_length=31, choices=States.choices())

    comment = models.TextField(blank=True)

    is_deleted = models.BooleanField(default=False)
    date_created = NonNaiveDateTimeField(auto_now_add=True)
    date_modified = NonNaiveDateTimeField(auto_now=True)
