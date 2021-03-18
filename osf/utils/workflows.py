# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum, IntEnum, unique


class ModerationEnum(IntEnum):
    '''A helper Enum superclass that provides easy translation to Int/CharChoices fields.'''

    @classmethod
    def int_field_choices(cls):
        return tuple((member.value, member.readable_value) for member in cls)

    @classmethod
    def char_field_choices(cls):
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
    UNAPPROVED = 1
    PENDING_MODERATION = 2
    APPROVED = 3
    REJECTED = 4
    MODERATOR_REJECTED = 5
    COMPLETED = 6  # Embargo only


class RegistrationModerationStates(ModerationEnum):
    '''The publication state of a Registration object'''
    UNDEFINED = 0
    INITIAL = 1
    REVERTED = 2
    PENDING = 3
    REJECTED = 4
    ACCEPTED = 5
    EMBARGO = 6
    PENDING_EMBARGO_TERMINATION = 7
    PENDING_WITHDRAW_REQUEST = 8
    PENDING_WITHDRAW = 9
    WITHDRAWN = 10

    @classmethod
    def from_sanction(cls, sanction):
        '''Returns a RegistrationModerationState based on sanction's type and state.'''
        # Define every time because it gets interpreted as an enum member in the class body :(
        SANCTION_STATE_MAP = {
            SanctionTypes.REGISTRATION_APPROVAL: {
                SanctionStates.UNAPPROVED: cls.INITIAL,
                SanctionStates.PENDING_MODERATION: cls.PENDING,
                SanctionStates.APPROVED: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.REVERTED,
                SanctionStates.MODERATOR_REJECTED: cls.REJECTED,
            },
            SanctionTypes.EMBARGO: {
                SanctionStates.UNAPPROVED: cls.INITIAL,
                SanctionStates.PENDING_MODERATION: cls.PENDING,
                SanctionStates.APPROVED: cls.EMBARGO,
                SanctionStates.COMPLETED: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.REVERTED,
                SanctionStates.MODERATOR_REJECTED: cls.REJECTED,
            },
            SanctionTypes.RETRACTION: {
                SanctionStates.UNAPPROVED: cls.PENDING_WITHDRAW_REQUEST,
                SanctionStates.PENDING_MODERATION: cls.PENDING_WITHDRAW,
                SanctionStates.APPROVED: cls.WITHDRAWN,
                # Rejected retractions are in either ACCEPTED or EMBARGO
                SanctionStates.REJECTED: cls.UNDEFINED,
                SanctionStates.MODERATOR_REJECTED: cls.UNDEFINED,
            },
            SanctionTypes.EMBARGO_TERMINATION_APPROVAL: {
                SanctionStates.UNAPPROVED: cls.PENDING_EMBARGO_TERMINATION,
                SanctionStates.PENDING_MODERATION: cls.ACCEPTED,  # Not currently reachable
                SanctionStates.APPROVED: cls.ACCEPTED,
                SanctionStates.REJECTED: cls.EMBARGO,
                SanctionStates.MODERATOR_REJECTED: cls.EMBARGO,  # Not currently reachable
            },
        }

        try:
            new_state = SANCTION_STATE_MAP[sanction.SANCTION_TYPE][sanction.approval_stage]
        except KeyError:
            new_state = cls.UNDEFINED

        return new_state


class RegistrationModerationTriggers(ModerationEnum):
    '''The acceptable 'triggers' to describe a moderated action on a Registration.'''

    SUBMIT = 0
    ACCEPT_SUBMISSION = 1
    REJECT_SUBMISSION = 2
    REQUEST_WITHDRAWAL = 3
    ACCEPT_WITHDRAWAL = 4
    REJECT_WITHDRAWAL = 5
    FORCE_WITHDRAW = 6

    @classmethod
    def from_transition(cls, from_state, to_state):
        '''Infer a trigger from a from_state/to_state pair.'''
        moderation_states = RegistrationModerationStates
        transition_to_trigger_mappings = {
            (moderation_states.INITIAL, moderation_states.PENDING): cls.SUBMIT,
            (moderation_states.PENDING, moderation_states.ACCEPTED): cls.ACCEPT_SUBMISSION,
            (moderation_states.PENDING, moderation_states.EMBARGO): cls.ACCEPT_SUBMISSION,
            (moderation_states.PENDING, moderation_states.REJECTED): cls.REJECT_SUBMISSION,
            (moderation_states.PENDING_WITHDRAW_REQUEST,
                moderation_states.PENDING_WITHDRAW): cls.REQUEST_WITHDRAWAL,
            (moderation_states.PENDING_WITHDRAW,
                moderation_states.WITHDRAWN): cls.ACCEPT_WITHDRAWAL,
            (moderation_states.PENDING_WITHDRAW, moderation_states.ACCEPTED): cls.REJECT_WITHDRAWAL,
            (moderation_states.PENDING_WITHDRAW, moderation_states.EMBARGO): cls.REJECT_WITHDRAWAL,
            (moderation_states.ACCEPTED, moderation_states.WITHDRAWN): cls.FORCE_WITHDRAW,
            (moderation_states.EMBARGO, moderation_states.WITHDRAWN): cls.FORCE_WITHDRAW,
        }
        return transition_to_trigger_mappings.get((from_state, to_state))


@unique
class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((v, str(v).title()) for v in cls.values())

    @classmethod
    def values(cls):
        return tuple(c.value for c in cls)

    @property
    def db_name(self):
        '''Return the value stored in the database for the enum member.

        For parity with ModerationEnum.
        '''
        return self.value


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
        'source': [SanctionStates.UNAPPROVED],
        'dest': None,
        'before': ['_validate_request'],
        'after': ['_on_approve'],
    },
    {
        # Allow delayed admin approvals as a noop in non-rejected states
        'trigger': 'approve',
        'source': [
            SanctionStates.PENDING_MODERATION,
            SanctionStates.APPROVED,
            SanctionStates.COMPLETED
        ],
        'dest': None,
    },
    {
        # A moderated sanction has satisfied its Admin approval requirements
        # and is submitted for moderation.
        # Allow calling without validation for use by OSF admins
        'trigger': 'accept',
        'source': [SanctionStates.UNAPPROVED],
        'dest': SanctionStates.PENDING_MODERATION,
        'conditions': ['is_moderated'],
        'before': ['_validate_request'],
        'after': [],  # send moderator emails here?
    },
    {
        # An un moderated sanction has satisfied its Admin approval requirements
        # or a moderated sanction recieves moderator approval and takes effect
        'trigger': 'accept',
        'source': [SanctionStates.UNAPPROVED, SanctionStates.PENDING_MODERATION],
        'dest': SanctionStates.APPROVED,
        'before': ['_validate_request'],
        'after': ['_on_complete'],
    },
    {
        # Allow delayed accept triggers as a noop in completed states
        'trigger': 'accept',
        'source': [SanctionStates.APPROVED, SanctionStates.COMPLETED],
        'dest': None,
    },
    {
        # A sanction is rejected by an admin
        'trigger': 'reject',
        'source': [SanctionStates.UNAPPROVED],
        'dest': SanctionStates.REJECTED,
        'before': ['_validate_request'],
        'after': ['_on_reject'],
    },
    {
        # A sanction is rejected by a moderator
        'trigger': 'reject',
        'source': [SanctionStates.PENDING_MODERATION],
        'dest': SanctionStates.MODERATOR_REJECTED,
        'before': ['_validate_request'],
        'after': ['_on_reject'],
    },
    {
        # Allow delayed reject triggers as a noop in rejected states
        'trigger': 'reject',
        'source': [SanctionStates.REJECTED, SanctionStates.MODERATOR_REJECTED],
        'dest': None,
    },
]

@unique
class RequestTypes(ChoiceEnum):
    ACCESS = 'access'
    WITHDRAWAL = 'withdrawal'
