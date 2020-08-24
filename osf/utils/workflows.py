
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum
from enum import unique

@unique
class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((v, str(v).title()) for v in cls.values())

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

REGISTRATION_TRIGGERS = DEFAULT_TRIGGERS + [
    ('EMBARGO', 'embargo'),
    ('WITHDRAW', 'withdraw'),
    ('REQUEST_WITHDRAW', 'request_withdraw'),
    ('REQUEST_EMBARGO', 'request_embargo'),
    ('REQUEST_EMBARGO_TERMINATION', 'request_embargo_termination'),
    ('TERMINATE_EMBARGO', 'terminate_embargo'),


]

REGISTRATION_STATES = REVIEW_STATES + [
    ('PENDING_EMBARGO', 'pending_embargo'),
    ('EMBARGO', 'embargo'),
    ('PENDING_EMBARGO_TERMINATION', 'pending_embargo_termination'),
    ('PENDING_WITHDRAW', 'pending_withdraw'),
]

DefaultStates = ChoiceEnum('DefaultStates', DEFAULT_STATES)
ReviewStates = ChoiceEnum('ReviewStates', REVIEW_STATES)
RegistrationStates = ChoiceEnum('RegistrationStates', REGISTRATION_STATES)
DefaultTriggers = ChoiceEnum('DefaultTriggers', DEFAULT_TRIGGERS)
ReviewTriggers = ChoiceEnum('ReviewTriggers', REVIEW_TRIGGERS)
RegistrationTriggers = ChoiceEnum('RegistrationTriggers', REGISTRATION_TRIGGERS)


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

REGISTRATION_TRANSITIONS = [
    {
        'trigger': DefaultTriggers.SUBMIT.value,
        'source': [DefaultStates.INITIAL.value],
        'dest': DefaultStates.PENDING.value,
        'after': ['save_action', 'update_last_transitioned', 'submit_draft_registration', 'notify_submit'],
    },
    {
        'trigger': DefaultTriggers.ACCEPT.value,
        'source': [DefaultStates.PENDING.value, DefaultStates.REJECTED.value],
        'dest': DefaultStates.ACCEPTED.value,
        'after': ['save_action', 'update_last_transitioned', 'accept_draft_registration', 'notify_accept_reject'],
    },
    {
        'trigger': DefaultTriggers.REJECT.value,
        'source': [DefaultStates.PENDING.value, DefaultStates.ACCEPTED.value],
        'dest': DefaultStates.REJECTED.value,
        'after': ['save_action', 'update_last_transitioned', 'reject_draft_registration', 'notify_accept_reject'],
    },
    {
        'trigger': RegistrationTriggers.EMBARGO.value,
        'source': [RegistrationStates.PENDING.value],
        'dest': RegistrationStates.EMBARGO.value,
        'after': ['save_action', 'update_last_transitioned', 'accept_draft_registration', 'embargo_registration', 'notify_embargo']
    },
    {
        'trigger': RegistrationTriggers.REQUEST_EMBARGO_TERMINATION.value,
        'source': [RegistrationStates.EMBARGO.value],
        'dest': RegistrationStates.PENDING_EMBARGO_TERMINATION.value,
        'after': ['save_action', 'update_last_transitioned', 'request_embargo_termination', 'notify_embargo_termination']
    },
    {
        'trigger': RegistrationTriggers.TERMINATE_EMBARGO.value,
        'source': [RegistrationStates.PENDING_EMBARGO_TERMINATION.value],
        'dest': RegistrationStates.ACCEPTED.value,
        'after': ['save_action', 'update_last_transitioned', 'terminate_embargo2', 'notify_embargo_termination']
    },
    {
        'trigger': RegistrationTriggers.REQUEST_WITHDRAW.value,
        'source': [RegistrationStates.ACCEPTED.value],
        'dest': RegistrationStates.PENDING_WITHDRAW.value,
        'after': ['save_action', 'update_last_transitioned', 'request_withdrawal', 'notify_withdraw']
    },
    {
        'trigger': RegistrationTriggers.WITHDRAW.value,
        'source': [RegistrationStates.PENDING_WITHDRAW.value],
        'dest': RegistrationStates.WITHDRAWN.value,
        'after': ['save_action', 'update_last_transitioned', 'withdraw_registration']
    }
]

@unique
class RequestTypes(ChoiceEnum):
    ACCESS = 'access'
    WITHDRAWAL = 'withdrawal'
