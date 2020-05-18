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
    creator = models.ForeignKey('OSFUser', related_name='submitted_%(class)s', on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)

    @property
    def target(self):
        raise NotImplementedError()


class NodeRequest(AbstractRequest, NodeRequestableMixin):
    """ Request for Node Access
    """
    target = models.ForeignKey('AbstractNode', related_name='requests', on_delete=models.CASCADE)


class PreprintRequest(AbstractRequest, PreprintRequestableMixin):
    """ Request for Preprint Withdrawal
    """
    target = models.ForeignKey('Preprint', related_name='requests', on_delete=models.CASCADE)
