# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum
from enum import unique


class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((v, unicode(v).title()) for v in cls.values())

    @classmethod
    def values(cls):
        return tuple(c.value for c in cls)


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
class Triggers(ChoiceEnum):
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
        'trigger': Triggers.SUBMIT.value,
        'source': [States.INITIAL.value],
        'dest': States.PENDING.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_submit'],
    },
    {
        'trigger': Triggers.SUBMIT.value,
        'source': [States.PENDING.value, States.REJECTED.value],
        'conditions': 'resubmission_allowed',
        'dest': States.PENDING.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_resubmit'],
    },
    {
        'trigger': Triggers.ACCEPT.value,
        'source': [States.PENDING.value, States.REJECTED.value],
        'dest': States.ACCEPTED.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_accept_reject'],
    },
    {
        'trigger': Triggers.REJECT.value,
        'source': [States.PENDING.value, States.ACCEPTED.value],
        'dest': States.REJECTED.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_accept_reject'],
    },
    {
        'trigger': Triggers.EDIT_COMMENT.value,
        'source': [States.PENDING.value, States.REJECTED.value, States.ACCEPTED.value],
        'dest': '=',
        'after': ['save_action', 'save_changes', 'notify_edit_comment'],
    },
]
