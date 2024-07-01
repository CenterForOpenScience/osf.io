from django.db import models

from .base import BaseModel, ObjectIDMixin
from osf.utils.workflows import (
    ApprovalStates,
    DefaultStates,
    DefaultTriggers,
    ReviewStates,
    ReviewTriggers,
    RegistrationModerationTriggers,
    RegistrationModerationStates,
    SchemaResponseTriggers,
    CollectionSubmissionStates,
    CollectionSubmissionsTriggers,
)
from osf.utils import permissions
from osf.utils.fields import NonNaiveDateTimeField


class BaseAction(ObjectIDMixin, BaseModel):
    class Meta:
        abstract = True

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
        choices=[(permission, permission.title()) for permission in permissions.API_CONTRIBUTOR_PERMISSIONS],
        default=permissions.READ
    )
    visible = models.BooleanField(default=True)


class PreprintRequestAction(BaseAction):
    target = models.ForeignKey('PreprintRequest', related_name='actions', on_delete=models.CASCADE)


class RegistrationAction(BaseAction):
    target = models.ForeignKey('Registration', related_name='actions', on_delete=models.CASCADE)

    trigger = models.CharField(
        max_length=31, choices=RegistrationModerationTriggers.char_field_choices())
    from_state = models.CharField(
        max_length=31, choices=RegistrationModerationStates.char_field_choices())
    to_state = models.CharField(
        max_length=31, choices=RegistrationModerationStates.char_field_choices())


class SchemaResponseAction(BaseAction):
    target = models.ForeignKey('SchemaResponse', related_name='actions', on_delete=models.CASCADE)
    trigger = models.CharField(max_length=31, choices=SchemaResponseTriggers.char_field_choices())
    from_state = models.CharField(max_length=31, choices=ApprovalStates.char_field_choices())
    to_state = models.CharField(max_length=31, choices=ApprovalStates.char_field_choices())


class CollectionSubmissionAction(ObjectIDMixin, BaseModel):
    creator = models.ForeignKey('OSFUser', related_name='+', on_delete=models.CASCADE)
    target = models.ForeignKey('CollectionSubmission', related_name='actions', on_delete=models.CASCADE)
    trigger = models.IntegerField(choices=CollectionSubmissionsTriggers.char_field_choices())
    from_state = models.IntegerField(choices=CollectionSubmissionStates.char_field_choices())
    to_state = models.IntegerField(choices=CollectionSubmissionStates.char_field_choices())
    comment = models.TextField(blank=True)

    deleted = NonNaiveDateTimeField(null=True, blank=True)
