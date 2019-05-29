# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from include import IncludeManager

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.workflows import DefaultStates, DefaultTriggers, ReviewStates, ReviewTriggers
from osf.utils import permissions


class BaseAction(ObjectIDMixin, BaseModel):
    class Meta:
        abstract = True

    objects = IncludeManager()

    creator = models.ForeignKey('OSFUser', related_name='+', on_delete=models.CASCADE)

    trigger = models.CharField(max_length=31, choices=DefaultTriggers.choices())
    from_state = models.CharField(max_length=31, choices=DefaultStates.choices())
    to_state = models.CharField(max_length=31, choices=DefaultStates.choices())

    comment = models.TextField(blank=True)

    is_deleted = models.BooleanField(default=False)
    auto = models.BooleanField(default=False)

    @property
    def target(self):
        raise NotImplementedError()


class ReviewAction(BaseAction):
    target = models.ForeignKey('Preprint', related_name='actions', on_delete=models.CASCADE)

    trigger = models.CharField(max_length=31, choices=ReviewTriggers.choices())
    from_state = models.CharField(max_length=31, choices=ReviewStates.choices())
    to_state = models.CharField(max_length=31, choices=ReviewStates.choices())


class NodeRequestAction(BaseAction):
    target = models.ForeignKey('NodeRequest', related_name='actions', on_delete=models.CASCADE)
    permissions = models.CharField(
        max_length=5,
        choices=[(permission, permission.title()) for permission in permissions.PERMISSIONS],
        default=permissions.READ
    )
    visible = models.BooleanField(default=True)


class PreprintRequestAction(BaseAction):
    target = models.ForeignKey('PreprintRequest', related_name='actions', on_delete=models.CASCADE)
