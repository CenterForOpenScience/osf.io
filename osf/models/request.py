from django.db import models
from .base import BaseModel, ObjectIDMixin
from osf.utils.workflows import RequestTypes, NodeRequestTypes
from .mixins import NodeRequestableMixin, PreprintRequestableMixin
from osf.utils.permissions import API_CONTRIBUTOR_PERMISSIONS


class AbstractRequest(BaseModel, ObjectIDMixin):
    class Meta:
        abstract = True

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
    request_type = models.CharField(
        max_length=31,
        choices=NodeRequestTypes.choices(),
        help_text='The specific type of node request (e.g., access request).'
    )
    requested_permissions = models.CharField(
        max_length=31,
        choices=((perm.lower(), perm) for perm in API_CONTRIBUTOR_PERMISSIONS),
        null=True,
        blank=True,
        help_text='The permissions being requested for the node (e.g., read, write, admin).'
    )


class PreprintRequest(AbstractRequest, PreprintRequestableMixin):
    """ Request for Preprint Withdrawal
    """
    target = models.ForeignKey('Preprint', related_name='requests', on_delete=models.CASCADE)
