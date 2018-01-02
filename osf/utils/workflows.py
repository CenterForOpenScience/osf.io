
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
class DefaultStates(ChoiceEnum):
    INITIAL = 'initial'
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'


@unique
class DefaultTriggers(ChoiceEnum):
    SUBMIT = 'submit'
    ACCEPT = 'accept'
    REJECT = 'reject'
    EDIT_COMMENT = 'edit_comment'

DEFAULT_TRANSITIONS = [
    {
        'trigger': DefaultTriggers.SUBMIT.value,
        'source': [DefaultStates.INITIAL.value],
        'dest': DefaultStates.PENDING.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_submit'],
    },
    {
        'trigger': DefaultTriggers.SUBMIT.value,
        'source': [DefaultStates.PENDING.value, DefaultStates.REJECTED.value],
        'conditions': 'resubmission_allowed',
        'dest': DefaultStates.PENDING.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_resubmit'],
    },
    {
        'trigger': DefaultTriggers.ACCEPT.value,
        'source': [DefaultStates.PENDING.value, DefaultStates.REJECTED.value],
        'dest': DefaultStates.ACCEPTED.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_accept_reject'],
    },
    {
        'trigger': DefaultTriggers.REJECT.value,
        'source': [DefaultStates.PENDING.value, DefaultStates.ACCEPTED.value],
        'dest': DefaultStates.REJECTED.value,
        'after': ['save_action', 'update_last_transitioned', 'save_changes', 'notify_accept_reject'],
    },
    {
        'trigger': DefaultTriggers.EDIT_COMMENT.value,
        'source': [DefaultStates.PENDING.value, DefaultStates.REJECTED.value, DefaultStates.ACCEPTED.value],
        'dest': '=',
        'after': ['save_action', 'save_changes', 'notify_edit_comment'],
    },
]
