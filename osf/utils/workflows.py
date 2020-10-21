# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum, IntEnum, unique


class ModerationEnum(IntEnum):
    '''A helper Enum superclass that provides easy translation to Int/CharChoices fields.'''

    @classmethod
    def int_choices(cls):
        return tuple((member.value, member.readable_value) for member in cls)

    @classmethod
    def char_choices(cls):
        return tuple((member.db_name, member.readable_value) for member in cls)

    @classmethod
    def from_db_name(cls, state_db_name):
        return cls[state_db_name.upper()]

    @property
    def readable_value(self):
        return super().name.title().replace('_', '')

    @property
    def db_name(self):
        return self.name.lower()


class SanctionTypes(ModerationEnum):
    '''A simple descriptor for the type of a sanction class'''

    UNDEFINED = 0
    REGISTRATION_APPROVAL = 1
    EMBARGO = 2
    RETRACTION = 3
    EMBARGO_TERMINATION_APPROVAL = 4
    DRAFT_REGISTRATION_APPROVAL = 5


class SanctionStates(ModerationEnum):
    '''The moderated state of a Sanction object.'''

    UNDEFINED = 0
    PENDING_ADMIN_APPROVAL = 1
    PENDING_MODERATOR_APPROVAL = 2
    ACCEPTED = 3
    REJECTED = 4
    COMPLETE = 5  # Embargo only


class RegistrationModerationStates(ModerationEnum):
    '''The publication state of a Registration object'''
    UNDEFINED = 0
    INITIAL = 1
    PENDING = 2
    REJECTED = 3
    ACCEPTED = 4
    EMBARGO = 5
    PENDING_EMBARGO_TERMINATION = 7
    PENDING_WITHDRAW_REQUEST = 8
    PENDING_WITHDRAW = 9
    WITHDRAWN = 10

    @classmethod
    def from_sanction(cls, sanction):
        '''Returns a RegistrationModerationState based on sanction's type and state.'''

        # Define every time because it can't exist in the class body :(
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
                SanctionStates.REJECTED: cls.UNDEFINED,  # Could be either ACCEPTED or EMBARGO
            },
            SanctionTypes.EMBARGO_TERMINATION_APPROVAL: {
                SanctionStates.PENDING_ADMIN_APPROVAL: cls.PENDING_EMBARGO_TERMINATION,
                SanctionStates.PENDING_MODERATOR_APPROVAL: cls.ACCEPTED,  # Should be unreachable
                SanctionStates.ACCEPTED: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.EMBARGO,
            },
        }

        return SANCTION_STATE_MAP[sanction.SANCTION_TYPE][sanction.approval_stage]


class RegistrationModerationTriggers(ModerationEnum):
    '''The acceptable 'triggers' to describe a moderated action on a Registration.'''

    SUBMIT = 0
    ACCEPT_SUBMISSION = 1
    REJECT_SUBMISSION = 2
    REQUEST_WITHDRAWAL = 3
    ACCEPT_WITHDRAWAL = 4
    REJECT_WITHDRAWAL = 5
    FORCE_WITHDRAW = 6

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

SANCTION_TRANSITIONS = [
    {
        # A single admin approves a sanction
        'trigger': 'approve',  # Approval from an individual admin
        'source': [SanctionStates.PENDING_ADMIN_APPROVAL],
        'dest': None,
        'before': ['_validate_request'],
        'after': ['_on_approve'],
    },
    {
        # A moderated sanction has satisfied its Admin approval requirements
        # and is submitted for moderation. Validation handled by approve chain.
        'trigger': 'accept',
        'source': [SanctionStates.PENDING_ADMIN_APPROVAL],
        'dest': SanctionStates.PENDING_MODERATOR_APPROVAL,
        'conditions': ['is_moderated'],
        'after': [],  # send moderator emails here?
    },
    {
        # An unmodrated sanction has satisfied its Admin approval requirements
        # and takes effect. Request validation handled via approve.
        'trigger': 'accept',
        'source': [SanctionStates.PENDING_ADMIN_APPROVAL],
        'dest': SanctionStates.ACCEPTED,
        'after': ['_on_complete'],
    },
    {
        # A moderaetd sanction is accepted by moderators and takes effect
        'trigger': 'accept',
        'source': [SanctionStates.PENDING_MODERATOR_APPROVAL],
        'dest': SanctionStates.ACCEPTED,
        'before': ['validate_request'],
        'after': ['_on_complete'],
    },
    {
        # A sanction is rejected by either an admin or a moderator
        'trigger': 'reject',
        'source': [SanctionStates.PENDING_MODERATOR_APPROVAL, SanctionStates.PENDING_ADMIN_APPROVAL],
        'dest': SanctionStates.REJECTED,
        'before': ['_validate_request'],
        'after': ['_on_reject'],
    },
]

@unique
class RequestTypes(ChoiceEnum):
    ACCESS = 'access'
    WITHDRAWAL = 'withdrawal'
