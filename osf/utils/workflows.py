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

    @classmethod
    def excluding(cls, *excluded_roles):
        return [role for role in cls if role not in excluded_roles]


class SanctionTypes(ModerationEnum):
    '''A simple descriptor for the type of a sanction class'''

    UNDEFINED = 0
    REGISTRATION_APPROVAL = 1
    EMBARGO = 2
    RETRACTION = 3
    EMBARGO_TERMINATION_APPROVAL = 4
    DRAFT_REGISTRATION_APPROVAL = 5


class ApprovalStates(ModerationEnum):
    '''The moderated state of a Sanction object.'''

    UNDEFINED = 0
    UNAPPROVED = 1
    PENDING_MODERATION = 2
    APPROVED = 3
    REJECTED = 4
    MODERATOR_REJECTED = 5
    COMPLETED = 6  # Embargo only
    IN_PROGRESS = 7  # Revisions only


class CollectionSubmissionStates(ModerationEnum):
    '''The states of a CollectionSubmission object.'''

    IN_PROGRESS = 1
    PENDING = 2
    REJECTED = 3
    ACCEPTED = 4
    REMOVED = 5


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
                ApprovalStates.UNAPPROVED: cls.INITIAL,
                ApprovalStates.PENDING_MODERATION: cls.PENDING,
                ApprovalStates.APPROVED: cls.ACCEPTED,
                ApprovalStates.REJECTED: cls.REVERTED,
                ApprovalStates.MODERATOR_REJECTED: cls.REJECTED,
            },
            SanctionTypes.EMBARGO: {
                ApprovalStates.UNAPPROVED: cls.INITIAL,
                ApprovalStates.PENDING_MODERATION: cls.PENDING,
                ApprovalStates.APPROVED: cls.EMBARGO,
                ApprovalStates.COMPLETED: cls.ACCEPTED,
                ApprovalStates.REJECTED: cls.REVERTED,
                ApprovalStates.MODERATOR_REJECTED: cls.REJECTED,
            },
            SanctionTypes.RETRACTION: {
                ApprovalStates.UNAPPROVED: cls.PENDING_WITHDRAW_REQUEST,
                ApprovalStates.PENDING_MODERATION: cls.PENDING_WITHDRAW,
                ApprovalStates.APPROVED: cls.WITHDRAWN,
                # Rejected retractions are in either ACCEPTED or EMBARGO
                ApprovalStates.REJECTED: cls.UNDEFINED,
                ApprovalStates.MODERATOR_REJECTED: cls.UNDEFINED,
            },
            SanctionTypes.EMBARGO_TERMINATION_APPROVAL: {
                ApprovalStates.UNAPPROVED: cls.PENDING_EMBARGO_TERMINATION,
                ApprovalStates.PENDING_MODERATION: cls.ACCEPTED,  # Not currently reachable
                ApprovalStates.APPROVED: cls.ACCEPTED,
                ApprovalStates.REJECTED: cls.EMBARGO,
                ApprovalStates.MODERATOR_REJECTED: cls.EMBARGO,  # Not currently reachable
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


class SchemaResponseTriggers(ModerationEnum):
    '''The acceptable 'triggers' to use with a SchemaResponseAction'''
    SUBMIT = 0
    APPROVE = 1  # Resource admins "approve" a submission
    ACCEPT = 2  # Moderators "accept" a submission
    ADMIN_REJECT = 3
    MODERATOR_REJECT = 4

    @classmethod
    def from_transition(cls, from_state, to_state):
        transition_to_trigger_mappings = {
            (ApprovalStates.IN_PROGRESS, ApprovalStates.UNAPPROVED): cls.SUBMIT,
            (ApprovalStates.UNAPPROVED, ApprovalStates.UNAPPROVED): cls.APPROVE,
            (ApprovalStates.UNAPPROVED, ApprovalStates.APPROVED): cls.APPROVE,
            (ApprovalStates.UNAPPROVED, ApprovalStates.PENDING_MODERATION): cls.APPROVE,
            (ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED): cls.ACCEPT,
            (ApprovalStates.UNAPPROVED, ApprovalStates.IN_PROGRESS): cls.ADMIN_REJECT,
            (ApprovalStates.PENDING_MODERATION, ApprovalStates.IN_PROGRESS): cls.MODERATOR_REJECT,
        }
        return transition_to_trigger_mappings.get((from_state, to_state))


class CollectionSubmissionsTriggers(ModerationEnum):
    '''The acceptable 'triggers' to use with a CollectionSubmissionsAction'''
    SUBMIT = 0
    ACCEPT = 1
    REJECT = 2
    REMOVE = 3
    RESUBMIT = 4
    CANCEL = 5


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

APPROVAL_TRANSITIONS = [
    {
        # Submit an approvable resource
        'trigger': 'submit',
        'source': [ApprovalStates.IN_PROGRESS],
        'dest': ApprovalStates.UNAPPROVED,
        'before': ['_validate_trigger'],
        'after': ['_on_submit'],
    },
    {
        # A single admin approves an approvable resource
        'trigger': 'approve',  # Approval from an individual admin
        'source': [ApprovalStates.UNAPPROVED],
        'dest': None,
        'before': ['_validate_trigger'],
        'after': ['_on_approve'],
    },
    {
        # Allow delayed admin approvals as a noop in non-rejected states
        'trigger': 'approve',
        'source': [
            ApprovalStates.PENDING_MODERATION,
            ApprovalStates.APPROVED,
            ApprovalStates.COMPLETED
        ],
        'dest': None,
    },
    {
        # A moderated approvable resource has satisfied its Admin approval
        # requirements and is submitted for moderation.
        'trigger': 'accept',
        'source': [ApprovalStates.UNAPPROVED],
        'dest': ApprovalStates.PENDING_MODERATION,
        'conditions': ['is_moderated'],
        'before': ['_validate_trigger'],
        'after': [],  # send moderator emails here?
    },
    {
        # An un moderated approvable resource has satisfied its Admin approval requirements
        # or a moderated sanction receives moderator approval and takes effect
        'trigger': 'accept',
        'source': [ApprovalStates.UNAPPROVED, ApprovalStates.PENDING_MODERATION],
        'dest': ApprovalStates.APPROVED,
        'before': ['_validate_trigger'],
        'after': ['_on_complete'],
    },
    {
        # Allow delayed accept triggers as a noop in completed states
        'trigger': 'accept',
        'source': [ApprovalStates.APPROVED, ApprovalStates.COMPLETED],
        'dest': None,
    },
    {
        # A revisable, approvable resource is rejected by an admin or moderator
        'trigger': 'reject',
        'source': [ApprovalStates.UNAPPROVED, ApprovalStates.PENDING_MODERATION],
        'dest': ApprovalStates.IN_PROGRESS,
        'conditions': ['revisable'],
        'before': ['_validate_trigger'],
        'after': ['_on_reject'],
    },
    {
        # An unrevisable, approvable resource is rejected by an admin
        'trigger': 'reject',
        'source': [ApprovalStates.UNAPPROVED],
        'dest': ApprovalStates.REJECTED,
        'before': ['_validate_trigger'],
        'after': ['_on_reject'],
    },
    {
        # An unrevisable, approvable entity is rejected by a moderator
        'trigger': 'reject',
        'source': [ApprovalStates.PENDING_MODERATION],
        'dest': ApprovalStates.MODERATOR_REJECTED,
        'before': ['_validate_trigger'],
        'after': ['_on_reject'],
    },
    {
        # Allow delayed reject triggers as a noop in rejected states
        'trigger': 'reject',
        'source': [ApprovalStates.REJECTED, ApprovalStates.MODERATOR_REJECTED],
        'dest': None,
    },
]


COLLECTION_SUBMISSION_TRANSITIONS = [
    {
        'trigger': 'submit',
        'source': [CollectionSubmissionStates.IN_PROGRESS],
        'dest': CollectionSubmissionStates.ACCEPTED,
        'before': [],
        'after': ['_notify_accepted'],
        'unless': ['is_moderated', 'is_hybrid_moderated'],
    },
    {
        'trigger': 'submit',
        'source': [CollectionSubmissionStates.IN_PROGRESS],
        'dest': CollectionSubmissionStates.PENDING,
        'before': [],
        'after': ['_notify_contributors_pending', '_notify_moderators_pending'],
        'conditions': ['is_moderated'],
    },
    {
        'trigger': 'submit',
        'source': [CollectionSubmissionStates.IN_PROGRESS],
        'dest': CollectionSubmissionStates.ACCEPTED,
        'before': [],
        'after': ['_notify_contributors_pending', '_notify_moderators_pending'],
        'conditions': ['is_hybrid_moderated', 'is_submitted_by_moderator_contributor'],
    },
    {
        'trigger': 'submit',
        'source': [CollectionSubmissionStates.IN_PROGRESS],
        'dest': CollectionSubmissionStates.PENDING,
        'before': [],
        'conditions': ['is_hybrid_moderated'],
        'after': ['_notify_contributors_pending', '_notify_moderators_pending'],
        'unless': ['is_submitted_by_moderator_contributor'],
    },
    {
        'trigger': 'accept',
        'source': [CollectionSubmissionStates.PENDING],
        'dest': CollectionSubmissionStates.ACCEPTED,
        'before': ['_validate_accept'],
        'after': ['_notify_accepted', '_make_public'],
        'conditions': ['is_moderated'],
    },
    {
        'trigger': 'accept',
        'source': [CollectionSubmissionStates.PENDING],
        'dest': CollectionSubmissionStates.ACCEPTED,
        'before': ['_validate_accept'],
        'after': ['_notify_accepted', '_make_public'],
        'conditions': ['is_hybrid_moderated'],
    },
    {
        'trigger': 'reject',
        'source': [CollectionSubmissionStates.PENDING],
        'dest': CollectionSubmissionStates.REJECTED,
        'before': ['_validate_reject'],
        'after': ['_notify_moderated_rejected'],
        'conditions': ['is_moderated'],
    },
    {
        'trigger': 'reject',
        'source': [CollectionSubmissionStates.PENDING],
        'dest': CollectionSubmissionStates.REJECTED,
        'before': ['_validate_reject'],
        'after': ['_notify_moderated_rejected'],
        'conditions': ['is_hybrid_moderated'],
    },
    {
        'trigger': 'remove',
        'source': [CollectionSubmissionStates.ACCEPTED],
        'dest': CollectionSubmissionStates.REMOVED,
        'before': ['_validate_remove'],
        'after': ['_remove_from_search', '_notify_removed'],
        'unless': ['is_hybrid_moderated', 'is_moderated'],
    },
    {
        'trigger': 'remove',
        'source': [CollectionSubmissionStates.ACCEPTED],
        'dest': CollectionSubmissionStates.REMOVED,
        'before': ['_validate_remove'],
        'after': ['_remove_from_search', '_notify_removed'],
        'conditions': ['is_hybrid_moderated'],
    },
    {
        'trigger': 'remove',
        'source': [CollectionSubmissionStates.ACCEPTED],
        'dest': CollectionSubmissionStates.REMOVED,
        'before': ['_validate_remove'],
        'after': ['_remove_from_search', '_notify_removed'],
        'conditions': ['is_moderated'],
    },
    {
        'trigger': 'resubmit',
        'source': [CollectionSubmissionStates.REJECTED, CollectionSubmissionStates.REMOVED],
        'dest': CollectionSubmissionStates.ACCEPTED,
        'before': ['_validate_resubmit'],
        'after': ['_make_public', '_notify_accepted'],
        'unless': ['is_moderated', 'is_hybrid_moderated'],
    },
    {
        'trigger': 'resubmit',
        'source': [CollectionSubmissionStates.REJECTED, CollectionSubmissionStates.REMOVED],
        'dest': CollectionSubmissionStates.PENDING,
        'before': ['_validate_resubmit'],
        'after': ['_make_public', '_notify_contributors_pending', '_notify_moderators_pending'],
        'conditions': ['is_moderated'],
    },
    {
        'trigger': 'resubmit',
        'source': [CollectionSubmissionStates.REJECTED, CollectionSubmissionStates.REMOVED],
        'dest': CollectionSubmissionStates.ACCEPTED,
        'before': [],
        'after': ['_make_public', '_notify_accepted'],
        'conditions': ['is_hybrid_moderated', 'is_submitted_by_moderator_contributor'],
    },
    {
        'trigger': 'resubmit',
        'source': [CollectionSubmissionStates.REJECTED, CollectionSubmissionStates.REMOVED],
        'dest': CollectionSubmissionStates.PENDING,
        'before': ['_validate_resubmit'],
        'after': ['_make_public', '_notify_contributors_pending', '_notify_moderators_pending'],
        'conditions': ['is_hybrid_moderated'],
        'unless': ['is_submitted_by_moderator_contributor']
    },
    {
        'trigger': 'cancel',
        'source': [CollectionSubmissionStates.PENDING],
        'dest': CollectionSubmissionStates.IN_PROGRESS,
        'before': ['_validate_cancel'],
        'after': ['_notify_cancel'],
        'conditions': [],
        'unless': []
    },
]

@unique
class RequestTypes(ChoiceEnum):
    ACCESS = 'access'
    WITHDRAWAL = 'withdrawal'
