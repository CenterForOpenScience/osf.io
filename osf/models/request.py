# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from include import IncludeManager

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.workflows import RequestTypes
from osf.models.mixins import RequestableMixin


class AbstractRequest(BaseModel, ObjectIDMixin, RequestableMixin):
    class Meta:
        abstract = True

    objects = IncludeManager()

    creator = models.ForeignKey('OSFUser', related_name='submitted_requests')
    request_type = models.CharField(max_length=31, choices=RequestTypes.choices())
    comment = models.TextField(null=True, blank=True)

    @property
    def target(self):
        raise NotImplementedError()


class NodeRequest(AbstractRequest):

    target = models.ForeignKey('AbstractNode', related_name='requests')
