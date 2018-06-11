
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum
from enum import unique

@unique
class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((v, unicode(v).title()) for v in cls.values())

    @classmethod
    def values(cls):
        return tuple(c.value for c in cls)

DEFAULT_STATES = [
    ('INITIAL', 'initial'),
    ('PENDING', 'pending'),
    ('ACCEPTED', 'accepted'),
    ('REJECTED', 'rejected'),
]
DEFAULT_TRIGGERS = [
    ('SUBMIT', 'submit'),
    ('ACCEPT', 'accept'),
    ('REJECT', 'reject'),
    ('EDIT_COMMENT', 'edit_comment'),
]
REVIEW_STATES = DEFAULT_STATES + [
    ('WITHDRAWN', 'withdrawn'),
]
REVIEW_TRIGGERS = DEFAULT_TRIGGERS + [
    ('WITHDRAW', 'withdraw')
]

DefaultStates = ChoiceEnum('DefaultStates', DEFAULT_STATES)
ReviewStates = ChoiceEnum('ReviewStates', REVIEW_STATES)
DefaultTriggers = ChoiceEnum('DefaultTriggers', DEFAULT_TRIGGERS)
ReviewTriggers = ChoiceEnum('ReviewTriggers', REVIEW_TRIGGERS)


CHRONOS_STATUS_STATES = [
    ('DRAFT', 1),
    ('SUBMITTED', 2),
    ('ACCEPTED', 3),
    ('PUBLISHED', 4),
    ('CANCELLED', 5),
]

ChronosSubmissionStatus = ChoiceEnum('ChronosSubmissionStatus', CHRONOS_STATUS_STATES)


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

REVIEWABLE_TRANSITIONS = DEFAULT_TRANSITIONS + [
    {
        'trigger': ReviewTriggers.WITHDRAW.value,
        'source': [ReviewStates.PENDING.value, ReviewStates.ACCEPTED.value],
        'dest': ReviewStates.WITHDRAWN.value,
        'after': ['save_action', 'update_last_transitioned', 'perform_withdraw', 'save_changes', 'notify_withdraw']
    }
]

@unique
class RequestTypes(ChoiceEnum):
    ACCESS = 'access'
    WITHDRAWAL = 'withdrawal'
