# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from include import IncludeManager

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.workflows import (
    ApprovalStates,
    DefaultStates,
    DefaultTriggers,
    ReviewStates,
    ReviewTriggers,
    RegistrationModerationTriggers,
    RegistrationModerationStates,
    SchemaResponseTriggers
)
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

    @classmethod
    def from_transition(cls, target, transition, user, comment):
        '''Generate a SchemaResponseAction based on a SchemaResposne object and a transition.'''
        from_state = ApprovalStates[transition.source]
        to_state = transition.dest
        to_state = ApprovalStates[to_state] if to_state is not None else from_state
        trigger = SchemaResponseTriggers.from_transition(from_state, to_state)
        if not trigger:
            raise ValueError(f'No action to write on transition from {from_state} to {to_state}')

        action = cls(
            target=target,
            creator=user,
            trigger=trigger.db_name,
            from_state=from_state.db_name,
            to_state=to_state.db_name,
            comment=comment
        )
        return action
