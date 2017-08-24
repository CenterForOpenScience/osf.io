# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import operator

from enum import Enum
from enum import unique

from django.db.models import Q


class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((w.value, unicode(w.value).title()) for w in cls)


@unique
class Workflows(ChoiceEnum):
    NONE = None
    PRE_MODERATION = 'pre-moderation'
    POST_MODERATION = 'post-moderation'


@unique
class States(ChoiceEnum):
    INITIAL = 'initial'
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'


@unique
class Actions(ChoiceEnum):
    SUBMIT = 'submit'
    ACCEPT = 'accept'
    REJECT = 'reject'
    EDIT_COMMENT = 'edit_comment'


PUBLIC_STATES = {
    Workflows.NONE.value: (
        States.INITIAL.value,
        States.PENDING.value,
        States.ACCEPTED.value,
        States.REJECTED.value,
    ),
    Workflows.PRE_MODERATION.value: (
        States.ACCEPTED.value,
    ),
    Workflows.POST_MODERATION.value: (
        States.PENDING.value,
        States.ACCEPTED.value,
    )
}


TRANSITIONS = [
    {
        'trigger': Actions.SUBMIT.value,
        'source': [States.INITIAL.value],
        'dest': States.PENDING.value,
        'after': ['save_log', 'update_last_transitioned', 'save_changes', 'notify_submit'],
    },
    {
        'trigger': Actions.SUBMIT.value,
        'source': [States.PENDING.value, States.REJECTED.value],
        'conditions': 'resubmission_allowed',
        'dest': States.PENDING.value,
        'after': ['save_log', 'update_last_transitioned', 'save_changes', 'notify_submit'],
    },
    {
        'trigger': Actions.ACCEPT.value,
        'source': [States.PENDING.value, States.REJECTED.value],
        'dest': States.ACCEPTED.value,
        'after': ['save_log', 'update_last_transitioned', 'save_changes', 'notify_accept'],
    },
    {
        'trigger': Actions.REJECT.value,
        'source': [States.PENDING.value, States.ACCEPTED.value],
        'dest': States.REJECTED.value,
        'after': ['save_log', 'update_last_transitioned', 'save_changes', 'notify_reject'],
    },
    {
        'trigger': Actions.EDIT_COMMENT.value,
        'source': [States.PENDING.value, States.REJECTED.value, States.ACCEPTED.value],
        'dest': '=',
        'after': ['save_log', 'save_changes', 'notify_edit_comment'],
    },
]


def public_reviewable_query():
    return functools.reduce(operator.or_, [
        Q(provider__reviews_workflow=workflow, reviews_state__in=public_states)
        for workflow, public_states in PUBLIC_STATES.items()
    ])
