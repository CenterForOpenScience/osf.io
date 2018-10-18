# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from include import IncludeManager

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.workflows import RequestTypes
from osf.models.mixins import NodeRequestableMixin, PreprintRequestableMixin


class AbstractRequest(BaseModel, ObjectIDMixin):
    class Meta:
        abstract = True

    objects = IncludeManager()

    request_type = models.CharField(max_length=31, choices=RequestTypes.choices())
    creator = models.ForeignKey('OSFUser', related_name='submitted_%(class)s')
    comment = models.TextField(null=True, blank=True)

    @property
    def target(self):
        raise NotImplementedError()


class NodeRequest(AbstractRequest, NodeRequestableMixin):
    target = models.ForeignKey('AbstractNode', related_name='requests')


class PreprintRequest(AbstractRequest, PreprintRequestableMixin):
    target = models.ForeignKey('Preprint', related_name='requests')
