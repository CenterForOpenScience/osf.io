
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum, IntEnum
from enum import unique


class ModerationEnum(IntEnum):

    @classmethod
    def int_choices(cls):
        return tuple((member.value, member.readable_name) for member in cls if member.value != 0)

    @classmethod
    def char_choices(cls):
        return tuple((member.db_name, member.readable_name) for member in cls if member.value != 0)

    @property
    def readable_value(self):
        return super().name.title().replace('_', '')

    @property
    def db_name(self):
        return self.name.lower()


class SanctionTypes(ModerationEnum):

    UNDEFINED = 0
    REGISTRATION_APPROVAL = 1
    EMBARGO = 2
    RETRACTION = 3
    EMBARGO_TERMINATION_APPROVAL = 4
    DRAFT_REGISTRATION_APPROVAL = 5


class SanctionStates(ModerationEnum):

    UNDEFINED = 0
    PENDING_ADMIN_APPROVAL = 1
    PENDING_MODERATOR_APPROVAL = 2
    ACCEPTED = 3
    REJECTED = 4
    COMPLETE = 5  # Embargo only


class RegistrationModerationStates(ModerationEnum):

    UNDEFINED = 0
    INITIAL = 1
    PENDING = 2
    REJECTED = 3
    ACCEPTED = 4
    EMBARGO = 5
    PENDING_EMBARGO_TERMINATION_REQUEST = 6
    PENDING_EMBARGO_TERMINATION = 7
    PENDING_WITHDRAW_REQUEST = 8
    PENDING_WITHDRAW = 9
    WITHDRAWN = 10

    @classmethod
    def from_sanction_and_state(cls, sanction_type, state):
        SANCTION_STATE_MAP = {
            SanctionTypes.REGISTRATION_APPROVAL: {
                SanctionStates.PENDING_ADMIN_APPROVAL: cls.INITIAL,
                SanctionStates.PENDING_MODERATOR_APPROVAL: cls.PENDING,
                SanctionStates.ACCEPTED: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.REJECTED,
            },
            SanctionTypes.EMBARGO: {
                SanctionStates.PENDING_ADMIN_APPROVAL: cls.INITIAL,
                SanctionStates.PENDING_MODERATOR_APPROVAL: cls.PENDING,
                SanctionStates.ACCEPTED: cls.EMBARGO,
                SanctionStates.COMPLETE: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.REJECTED,
            },
            SanctionTypes.RETRACTION: {
                SanctionStates.PENDING_ADMIN_APPROVAL: cls.PENDING_WITHDRAW_REQUEST,
                SanctionStates.PENDING_MODERATOR_APPROVAL: cls.PENDING_WITHDRAW,
                SanctionStates.ACCEPTED: cls.WITHDRAWN,
                SanctionStates.REJECTED: cls.UNDEFINED,  # Either ACCEPTED or EMBARGO
            },
            SanctionTypes.EMBARGO_TERMINATION_APPROVAL: {
                SanctionStates.PENDING_ADMIN_APPROVAL: cls.PENDING_EMBARGO_TERMINATION_REQUEST,
                SanctionStates.PENDING_MODERATOR_APPROVAL: cls.PENDING_EMBARGO_TERMINATION,
                SanctionStates.ACCEPTED: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.EMBARGO,
            },
        }

        return SANCTION_STATE_MAP[sanction_type][state]


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
    ('WITHDRAW_REQUEST_FAILS', 'withdraw_request_fails'),
    ('WITHDRAW_REQUEST_PASSES', 'withdraw_request_pass'),
    ('REJECT_WITHDRAW', 'reject_withdraw'),
    ('FORCE_WITHDRAW', 'force_withdraw'),
    ('REQUEST_EMBARGO', 'request_embargo'),
    ('REQUEST_EMBARGO_TERMINATION', 'request_embargo_termination'),
    ('TERMINATE_EMBARGO', 'terminate_embargo'),


]

REGISTRATION_STATES = REVIEW_STATES + [
    ('EMBARGO', 'embargo'),
    ('PENDING_EMBARGO_TERMINATION', 'pending_embargo_termination'),
    ('PENDING_WITHDRAW_REQUEST', 'pending_withdraw_request'),
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
        'trigger': RegistrationTriggers.SUBMIT.value,
        'source': [RegistrationStates.INITIAL.value],
        'dest': RegistrationStates.ACCEPTED.value,
        'unless': ['is_moderated', 'is_embargoed'],
        'after': ['save_action', 'update_last_transitioned', 'accept_registration', 'notify_accept_reject']
    },
    {
        'trigger': RegistrationTriggers.SUBMIT.value,
        'source': [RegistrationStates.INITIAL.value],
        'dest': RegistrationStates.EMBARGO.value,
        'unless': ['is_moderated'],
        'after': ['save_action', 'update_last_transitioned', 'embargo_registration', 'notify_accept_reject']
    },

    {
        'trigger': RegistrationTriggers.SUBMIT.value,
        'source': [RegistrationStates.INITIAL.value],
        'dest': RegistrationStates.PENDING.value,
        'after': ['save_action', 'update_last_transitioned', 'submit_registration', 'notify_submit'],
    },
    {
        'trigger': RegistrationTriggers.ACCEPT.value,
        'source': [RegistrationStates.PENDING.value],
        'dest': RegistrationStates.ACCEPTED.value,
        'unless': ['is_embargoed'],
        'after': ['save_action', 'update_last_transitioned', 'accept_registration', 'notify_accept_reject'],
    },
    {
        'trigger': RegistrationTriggers.ACCEPT.value,
        'source': [RegistrationStates.PENDING.value],
        'dest': RegistrationStates.EMBARGO.value,
        'after': ['save_action', 'update_last_transitioned', 'notify_accept_reject']
    },
    {
        'trigger': RegistrationTriggers.REJECT.value,
        'source': [RegistrationStates.PENDING.value],
        'dest': RegistrationStates.REJECTED.value,
        'after': ['save_action', 'update_last_transitioned', 'reject_registration', 'notify_accept_reject'],
    },
    {
        'trigger': RegistrationTriggers.FORCE_WITHDRAW.value,
        'source': [RegistrationStates.ACCEPTED.value, RegistrationStates.EMBARGO.value, RegistrationStates.PENDING_WITHDRAW.value],
        'dest': RegistrationStates.WITHDRAWN.value,
        'after': ['save_action', 'update_last_transitioned', 'force_withdrawal', 'notify_accept_reject'],
    },
    {
        'trigger': RegistrationTriggers.REQUEST_EMBARGO_TERMINATION.value,
        'source': [RegistrationStates.EMBARGO.value],
        'dest': RegistrationStates.PENDING_EMBARGO_TERMINATION.value,
        'after': ['save_action', 'update_last_transitioned', 'request_terminate_embargo', 'notify_embargo_termination']
    },
    {
        'trigger': RegistrationTriggers.TERMINATE_EMBARGO.value,
        'source': [RegistrationStates.PENDING_EMBARGO_TERMINATION.value],
        'dest': RegistrationStates.ACCEPTED.value,
        'after': ['save_action', 'update_last_transitioned', 'terminate_embargo', 'notify_embargo_termination']
    },
    {
        'trigger': RegistrationTriggers.REQUEST_WITHDRAW.value,
        'source': [RegistrationStates.ACCEPTED.value, RegistrationStates.EMBARGO.value],
        'dest': RegistrationStates.PENDING_WITHDRAW_REQUEST.value,
        'after': ['save_action', 'update_last_transitioned', 'request_withdrawal', 'notify_withdraw_request']
    },
    {
        'trigger': RegistrationTriggers.WITHDRAW_REQUEST_PASSES.value,
        'source': [RegistrationStates.PENDING_WITHDRAW_REQUEST.value],
        'dest': RegistrationStates.WITHDRAWN.value,
        'unless': ['is_moderated'],
        'after': ['save_action', 'update_last_transitioned', 'withdraw_registration'],
    },
    {
        'trigger': RegistrationTriggers.WITHDRAW_REQUEST_PASSES.value,
        'source': [RegistrationStates.PENDING_WITHDRAW_REQUEST.value],
        'dest': RegistrationStates.PENDING_WITHDRAW.value,
        'after': ['save_action', 'update_last_transitioned', 'notify_withdraw_request_submitted']
    },
    {
        'trigger': RegistrationTriggers.WITHDRAW_REQUEST_FAILS.value,
        'source': [RegistrationStates.PENDING_WITHDRAW_REQUEST.value],
        'dest': RegistrationStates.ACCEPTED.value,
        'unless': 'is_embargoed',
        'after': ['save_action', 'update_last_transitioned', 'notify_withdraw_request_denied', 'withdrawal_request_fails']
    },
    {
        'trigger': RegistrationTriggers.WITHDRAW_REQUEST_FAILS.value,
        'source': [RegistrationStates.PENDING_WITHDRAW_REQUEST.value],
        'dest': RegistrationStates.EMBARGO.value,
        'after': ['save_action', 'update_last_transitioned', 'notify_withdraw_request_denied', 'withdrawal_request_fails']
    },
    {
        'trigger': RegistrationTriggers.WITHDRAW.value,
        'source': [RegistrationStates.PENDING_WITHDRAW.value],
        'dest': RegistrationStates.WITHDRAWN.value,
        'after': ['save_action', 'update_last_transitioned', 'withdraw_registration']
    },
    {
        'trigger': RegistrationTriggers.REJECT_WITHDRAW.value,
        'source': [RegistrationStates.PENDING_WITHDRAW.value],
        'dest': RegistrationStates.ACCEPTED.value,
        'after': ['save_action', 'update_last_transitioned', 'reject_withdrawal', 'notify_withdraw']
    }
]


SANCTION_TRANSITIONS = [
    {
        'trigger': 'accept',
        'source': [SanctionStates.PENDING_ADMIN_APPROVAL],
        'dest': SanctionStates.PENDING_MODERATOR_APPROVAL,
        'cond': ['is_moderated'],
    },
    {
        'trigger': 'accept',
        'source': [SanctionStates.PENDING_MODERATOR_APPROVAL, SanctionStates.PENDING_ADMIN_APPROVAL],
        'dest': SanctionStates.ACCEPTED,
        'after': ['_on_complete']
    },
    {
        'trigger': 'deny',
        'source': ['*'],
        'dest': SanctionStates.REJECTED,
        'after': ['_on_reject']
    },
]

@unique
class RequestTypes(ChoiceEnum):
    ACCESS = 'access'
    WITHDRAWAL = 'withdrawal'
