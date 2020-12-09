import pytz
import functools

from api.share.utils import update_share

from dateutil.parser import parse as parse_date
from django.apps import apps
from django.utils import timezone
from django.conf import settings
from django.db import models

from osf.utils.fields import NonNaiveDateTimeField

from framework.auth import Auth
from framework.exceptions import PermissionsError
from website import settings as osf_settings
from website import mails
from osf.exceptions import (
    InvalidSanctionRejectionToken,
    InvalidSanctionApprovalToken,
    NodeStateError,
)

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils import tokens
from osf.utils.machines import SanctionStateMachine
from osf.utils.workflows import SanctionStates, SanctionTypes

VIEW_PROJECT_URL_TEMPLATE = osf_settings.DOMAIN + '{node_id}/'


class Sanction(ObjectIDMixin, BaseModel, SanctionStateMachine):
    """Sanction class is a generic way to track approval states"""
    # Neither approved not cancelled
    UNAPPROVED = SanctionStates.UNAPPROVED.db_name
    # Has approval
    APPROVED = SanctionStates.APPROVED.db_name
    # Rejected by at least one contributor
    REJECTED = SanctionStates.REJECTED.db_name
    # Embargo has been completed
    COMPLETED = SanctionStates.COMPLETED.db_name
    # Approved by admins but pending moderator approval/rejection
    PENDING_MODERATION = SanctionStates.PENDING_MODERATION.db_name
    # Rejected by a moderator
    MODERATOR_REJECTED = SanctionStates.MODERATOR_REJECTED.db_name

    SANCTION_TYPE = SanctionTypes.UNDEFINED
    DISPLAY_NAME = 'Sanction'
    # SHORT_NAME must correspond with the associated foreign field to query against,
    # e.g. Node.find_one(Q(sanction.SHORT_NAME, 'eq', sanction))
    SHORT_NAME = 'sanction'

    ACTION_NOT_AUTHORIZED_MESSAGE = 'This user is not authorized to {ACTION} this {DISPLAY_NAME}'
    APPROVAL_INVALID_TOKEN_MESSAGE = 'Invalid approval token provided for this {DISPLAY_NAME}.'
    REJECTION_INVALID_TOKEN_MESSAGE = 'Invalid rejection token provided for this {DISPLAY_NAME}.'

    # Controls whether or not the Sanction needs unanimous approval or just a single approval
    ANY = 'any'
    UNANIMOUS = 'unanimous'
    mode = UNANIMOUS

    # Sanction subclasses must have an initiated_by field
    # initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)

    # Expanded: Dictionary field mapping admin IDs their approval status and relevant tokens:
    # {
    #   'b3k97': {
    #     'has_approved': False,
    #     'approval_token': 'Pew7wj1Puf7DENUPFPnXSwa1rf3xPN',
    #     'rejection_token': 'TwozClTFOic2PYxHDStby94bCQMwJy'}
    # }
    approval_state = DateTimeAwareJSONField(default=dict, blank=True)

    # Expiration date-- Sanctions in the UNAPPROVED state that are older than their end_date
    # are automatically made ACTIVE by a daily cron job
    # Use end_date=None for a non-expiring Sanction
    end_date = NonNaiveDateTimeField(null=True, blank=True, default=None)
    initiation_date = NonNaiveDateTimeField(default=timezone.now, null=True, blank=True)

    state = models.CharField(choices=SanctionStates.char_field_choices(),
                             default=UNAPPROVED,
                             max_length=255)

    def __repr__(self):
        return '<{self.__class__.__name__}(end_date={self.end_date!r}) with _id {self._id!r}>'.format(
            self=self)

    @property
    def is_pending_approval(self):
        '''The sanction is awaiting admin approval.'''
        return self.approval_stage is SanctionStates.UNAPPROVED

    @property
    def is_approved(self):
        '''The sanction has received all required admin and moderator approvals.'''
        return self.approval_stage is SanctionStates.APPROVED

    @property
    def is_rejected(self):
        '''The sanction has been rejected by either an admin or a moderator.'''
        rejected_states = [
            SanctionStates.REJECTED, SanctionStates.MODERATOR_REJECTED
        ]
        return self.approval_stage in rejected_states

    @property
    def is_moderated(self):
        return self.target_registration.is_moderated

    @property
    def approval_stage(self):
        return SanctionStates.from_db_name(self.state)

    @approval_stage.setter
    def approval_stage(self, state):
        self.state = state.db_name

    @property
    def target_registration(self):
        return self._get_registration()

    # The Sanction object will also inherit the following functions from the SanctionStateMachine:
    #
    # approve(self, user, token)
    # accept(self, user, token)
    # reject(self, user, token)
    #
    # Overrriding these functions will divorce the offending Sanction class from that trigger's
    # functionality on the state machine.

    def _get_registration(self):
        """Get the Registration that is waiting on this sanction."""
        raise NotImplementedError('Sanction subclasses must implement a #_get_registration method')

    def _on_approve(self, event_data):
        """Callback for individual admin approval of a sanction.

        Invoked by state machine as the last step of an 'approve' trigger

        :param EventData event_data: An EventData object from transitions.core
            contains information about the active state transition and arbitrary args and kwargs
        """
        raise NotImplementedError(
            'Sanction subclasses must implement an #_on_approve method')

    def _on_reject(self, event_data):
        """Callback for rejection of a Sanction.

        Invoked by state machine as the last step of a 'reject' trigger

        :param EventData event_data: An EventData object from transitions.core
            contains information about the active state transition and arbitrary args and kwargs
        """
        raise NotImplementedError(
            'Sanction subclasses must implement an #_on_reject method')

    def _on_complete(self, user):
        """Callback for when a Sanction is fully approved.

        Invoked by state machine as the last step of an 'accept' trigger

        :param EventData event_data: An EventData object from transitions.core
            contains information about the active state transition and arbitrary args and kwargs
        """
        raise NotImplementedError(
            'Sanction subclasses must implement an #_on_complete method')

    def forcibly_reject(self):
        self.state = Sanction.REJECTED

    class Meta:
        abstract = True


class TokenApprovableSanction(Sanction):
    def _validate_authorizer(self, user):
        """Subclasses may choose to provide extra restrictions on who can be an authorizer
        :return Boolean: True if user is allowed to be an authorizer else False
        """
        return True

    def _verify_user_role(self, user, action):
        '''Confirm that user is allowed to act on the sanction in its current approval_stage.'''
        if self.approval_stage is SanctionStates.UNAPPROVED:
            # Allow user is None when UNAPPROVED to support timed
            # sanction expiration from within OSF via the 'accept' trigger
            if user is None or user._id in self.approval_state:
                return True
            return False

        required_permission = f'{action}_submissions'
        if self.approval_stage is SanctionStates.PENDING_MODERATION:
            return user.has_perm(required_permission, self.target_registration.provider)

        return False

    def _validate_request(self, event_data):
        '''Verify that an approve/accept/reject call meets all preconditions.'''
        action = event_data.event.name
        user = event_data.kwargs.get('user')
        if user is None and event_data.args:
            user = event_data.args[0]
        # Allow certain 'accept' calls with no user for OSF admin use
        if not user and action != 'accept':
            raise ValueError('All state trigger functions must specify a user')

        if not self._verify_user_role(user, action):
            raise PermissionsError(self.ACTION_NOT_AUTHORIZED_MESSAGE.format(
                ACTION=action, DISPLAY_NAME=self.DISPLAY_NAME))

        # Moderator auth is validated by API, no token to check
        # user is None and no prior exception -> OSF-internal accept call
        if self.approval_stage is SanctionStates.PENDING_MODERATION or user is None:
            return True

        token = event_data.kwargs.get('token')
        if token is None:
            try:
                token = event_data.args[1]
            except IndexError:
                raise ValueError('Admin actions require a token')

        if action == 'approve' and self.approval_state[user._id]['approval_token'] != token:
            raise InvalidSanctionApprovalToken(
                self.APPROVAL_INVALID_TOKEN_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        elif action == 'reject' and self.approval_state[user._id]['rejection_token'] != token:
            raise InvalidSanctionRejectionToken(
                self.REJECTION_INVALID_TOKEN_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))

        return True

    def add_authorizer(self, user, node, approved=False, save=False):
        """Add an admin user to this Sanction's approval state.

        :param User user: User to add.
        :param Node registration: The pending registration node.
        :param bool approved: Whether `user` has approved.
        :param bool save: Whether to save this object.
        """

        valid = self._validate_authorizer(user)
        if not valid or user._id in self.approval_state:
            return False

        self.approval_state[user._id] = {
            'has_approved': approved,
            'node_id': node._id,
            'approval_token': tokens.encode({
                'user_id': user.id,
                'sanction_id': self._id,
                'action': 'approve_{}'.format(self.SHORT_NAME)
            }),
            'rejection_token': tokens.encode({
                'user_id': user.id,
                'sanction_id': self._id,
                'action': 'reject_{}'.format(self.SHORT_NAME)
            })
        }

        if save:
            self.save()

        return True

    def remove_authorizer(self, user, save=False):
        """Remove a user as an authorizer

        :param User user:
        :return Boolean: True if user is removed else False
        """
        if user._id not in self.approval_state:
            return False

        del self.approval_state[user._id]
        if save:
            self.save()
        return True

    def _on_approve(self, event_data):
        """Callback from #approve state machine trigger.

        Calls #accept trigger under either of two conditions:
        - mode is ANY and the Sanction has not already been cancelled
        - mode is UNANIMOUS and all users have given approval
        """
        user = event_data.kwargs.get('user')
        if user is None and event_data.args:
            user = event_data.args[0]
        self.approval_state[user._id]['has_approved'] = True

        if self.mode == self.ANY or all(
                authorizer['has_approved']
                for authorizer in self.approval_state.values()):
            self.accept(*event_data.args, **event_data.kwargs)  # state machine trigger

    def token_for_user(self, user, method):
        """
        :param str method: 'approval' | 'rejection'
        """
        try:
            user_state = self.approval_state[user._id]
        except KeyError:
            raise PermissionsError(self.APPROVAL_NOT_AUTHORIZED_MESSAGE.format(
                DISPLAY_NAME=self.DISPLAY_NAME))
        return user_state['{0}_token'.format(method)]

    def _notify_authorizer(self, user, node):
        pass

    def _notify_non_authorizer(self, user, node):
        pass

    def ask(self, group):
        pass

    class Meta:
        abstract = True


class EmailApprovableSanction(TokenApprovableSanction):
    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = None
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = None

    VIEW_URL_TEMPLATE = ''
    APPROVE_URL_TEMPLATE = ''
    REJECT_URL_TEMPLATE = ''

    # A flag to conditionally run a callback on complete
    notify_initiator_on_complete = models.BooleanField(default=False)
    # Store a persistant copy of urls for use when needed outside of a request context.
    # This field gets automagically updated whenever models approval_state is modified
    # and the model is saved
    # {
    #   'abcde': {
    #     'approve': [APPROVAL_URL],
    #     'reject': [REJECT_URL],
    #   }
    # }
    stashed_urls = DateTimeAwareJSONField(default=dict, blank=True)

    @property
    def should_suppress_emails(self):
        return self._get_registration().external_registration

    @staticmethod
    def _format_or_empty(template, context):
        if context:
            return template.format(**context)
        return ''

    def _view_url(self, user_id, node):
        return self._format_or_empty(self.VIEW_URL_TEMPLATE,
                                     self._view_url_context(user_id, node))

    def _view_url_context(self, user_id, node):
        return None

    def _approval_url(self, user_id):
        return self._format_or_empty(self.APPROVE_URL_TEMPLATE,
                                     self._approval_url_context(user_id))

    def _approval_url_context(self, user_id):
        return None

    def _rejection_url(self, user_id):
        return self._format_or_empty(self.REJECT_URL_TEMPLATE,
                                     self._rejection_url_context(user_id))

    def _rejection_url_context(self, user_id):
        return None

    def _send_approval_request_email(self, user, template, context):
        mails.send_mail(user.username, template, user=user, can_change_preferences=False, **context)

    def _email_template_context(self, user, node, is_authorizer=False):
        return {}

    def _notify_authorizer(self, authorizer, node):
        context = self._email_template_context(authorizer,
                                            node,
                                            is_authorizer=True)
        if self.AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(
                authorizer, self.AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError()

    def _notify_non_authorizer(self, user, node):
        context = self._email_template_context(user, node)
        if self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(
                user, self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError

    def ask(self, group):
        """
        :param list group: List of (user, node) tuples containing contributors to notify about the
        sanction.
        """
        if self.should_suppress_emails:
            return
        for contrib, node in group:
            if contrib._id in self.approval_state:
                self._notify_authorizer(contrib, node)
            else:
                self._notify_non_authorizer(contrib, node)

    def add_authorizer(self, user, node, **kwargs):
        super(EmailApprovableSanction, self).add_authorizer(user, node,
                                                            **kwargs)
        self.stashed_urls[user._id] = {
            'view': self._view_url(user._id, node),
            'approve': self._approval_url(user._id),
            'reject': self._rejection_url(user._id)
        }
        self.save()

    def _notify_initiator(self):
        raise NotImplementedError

    def _on_complete(self, event_data):
        if self.notify_initiator_on_complete and not self.should_suppress_emails:
            self._notify_initiator()

    class Meta:
        abstract = True


class SanctionCallbackMixin(object):
    def _notify_initiator(self):
        raise NotImplementedError()

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        return {}


class Embargo(SanctionCallbackMixin, EmailApprovableSanction):
    """Embargo object for registrations waiting to go public."""
    SANCTION_TYPE = SanctionTypes.EMBARGO
    DISPLAY_NAME = 'Embargo'
    SHORT_NAME = 'embargo'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'

    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    for_existing_registration = models.BooleanField(default=False)

    @property
    def is_completed(self):
        return self.state == self.COMPLETED

    @property
    def is_deleted(self):
        if self.target_registration:
            return self.target_registration.is_deleted
        else:  # Embargo is orphaned, so consider it deleted
            return True

    @property
    def embargo_end_date(self):
        if self.state == self.APPROVED:
            return self.end_date
        return False

    # NOTE(hrybacki): Old, private registrations are grandfathered and do not
    # require to be made public or embargoed. This field differentiates them
    # from new registrations entering into an embargo field which should not
    # show up in any search related fields.
    @property
    def pending_registration(self):
        return not self.for_existing_registration and self.is_pending_approval

        # def __repr__(self):
        #     pass
        # from osf.models import Node
        #
        # parent_registration = None
        # try:
        #     parent_registration = Node.find_one(Q('embargo', 'eq', self))
        # except NoResultsFound:
        #     pass
        # return ('<Embargo(parent_registration={0}, initiated_by={1}, '
        #         'end_date={2}) with _id {3}>').format(
        #     parent_registration,
        #     self.initiated_by,
        #     self.end_date,
        #     self._id
        # )

    def _get_registration(self):
        return self.registrations.first()

    def _view_url_context(self, user_id, node):
        registration = node or self._get_registration()
        return {'node_id': registration._id}

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            registration = self._get_registration()
            node_id = user_approval_state.get('node_id', registration._id)
            return {'node_id': node_id, 'token': approval_token}

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = user_approval_state.get('rejection_token')
        if rejection_token:
            Registration = apps.get_model('osf.Registration')
            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Registration.load(node_id)
            return {
                'node_id': registration.registered_from._id,
                'token': rejection_token,
            }

    def _email_template_context(self,
                                user,
                                node,
                                is_authorizer=False,
                                urls=None):
        context = super(Embargo, self)._email_template_context(
            user,
            node,
            is_authorizer=is_authorizer)
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = osf_settings.EMBARGO_PENDING_TIME.days * 24

            registration = self._get_registration()

            context.update({
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
                'approval_link': approval_link,
                'project_name': registration.title,
                'disapproval_link': disapproval_link,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
                'approval_time_span': approval_time_span,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
            })
        return context

    def _on_reject(self, event_data):
        user = event_data.kwargs.get('user')
        if user is None and event_data.args:
            user = event_data.args[0]
        NodeLog = apps.get_model('osf.NodeLog')

        parent_registration = self.target_registration
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_CANCELLED,
            params={
                'node': parent_registration.registered_from._id,
                'registration': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(user) if user else Auth(self.initiated_by))
        # Remove backref to parent project if embargo was for a new registration
        if not self.for_existing_registration:
            parent_registration.delete_registration_tree(save=True)
            parent_registration.registered_from = None
        # Delete parent registration if it was created at the time the embargo was initiated
        if not self.for_existing_registration:
            parent_registration.is_deleted = True
            parent_registration.deleted = timezone.now()
            parent_registration.save()

    def disapprove_embargo(self, user, token):
        """Cancels retraction if user is admin and token verifies."""
        self.reject(user=user, token=token)

    def _on_complete(self, event_data):
        NodeLog = apps.get_model('osf.NodeLog')

        parent_registration = self.target_registration
        if parent_registration.is_spammy:
            raise NodeStateError('Cannot complete a spammy registration.')

        super()._on_complete(event_data)
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_APPROVED,
            params={
                'node': parent_registration.registered_from._id,
                'registration': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(self.initiated_by), )
        self.save()

    def approve_embargo(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        self.approve(user=user, token=token)

    def mark_as_completed(self):
        # Plucked from embargo_registrations script
        # self.state = Sanction.COMPLETED
        self.to_COMPLETED()

class Retraction(EmailApprovableSanction):
    """
    Retraction object for public registrations.
    Externally (specifically in user-facing language) retractions should be referred to as "Withdrawals", i.e.
    "Retract Registration" -> "Withdraw Registration", "Retracted" -> "Withdrawn", etc.
    """
    SANCTION_TYPE = SanctionTypes.RETRACTION
    DISPLAY_NAME = 'Retraction'
    SHORT_NAME = 'retraction'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_RETRACTION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_RETRACTION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'

    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    justification = models.CharField(max_length=2048, null=True, blank=True)
    date_retracted = NonNaiveDateTimeField(null=True, blank=True)

    def _get_registration(self):
        Registration = apps.get_model('osf.Registration')
        parent_registration = Registration.objects.get(retraction=self)

        return parent_registration

    def _view_url_context(self, user_id, node):
        registration = self.registrations.first() or node
        return {
            'node_id': registration._id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            root_registration = self.registrations.first()
            node_id = user_approval_state.get('node_id', root_registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = user_approval_state.get('rejection_token')
        if rejection_token:
            Registration = apps.get_model('osf.Registration')
            node_id = user_approval_state.get('node_id', None)
            registration = Registration.objects.select_related(
                'registered_from'
            ).get(
                guids___id=node_id, guids___id__isnull=False
            ) if node_id else self.registrations.first()

            return {
                'node_id': registration.registered_from._id,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = osf_settings.RETRACTION_PENDING_TIME.days * 24

            return {
                'is_initiator': self.initiated_by == user,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
                'initiated_by': self.initiated_by.fullname,
                'project_name': self.registrations.filter().values_list('title', flat=True).get(),
                'registration_link': registration_link,
                'approval_link': approval_link,
                'disapproval_link': disapproval_link,
                'approval_time_span': approval_time_span,
            }
        else:
            return {
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
            }

    def _on_reject(self, event_data):
        user = event_data.kwargs.get('user')
        if user is None and event_data.args:
            user = event_data.args[0]

        NodeLog = apps.get_model('osf.NodeLog')
        parent_registration = self.target_registration
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_CANCELLED,
            params={
                'node': parent_registration.registered_from._id,
                'registration': parent_registration._id,
                'retraction_id': self._id,
            },
            auth=Auth(user),
            save=True,
        )

    def _on_complete(self, event_data):
        super()._on_complete(event_data)
        NodeLog = apps.get_model('osf.NodeLog')

        self.date_retracted = timezone.now()
        self.save()

        parent_registration = self.target_registration
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_APPROVED,
            params={
                'node': parent_registration.registered_from._id,
                'retraction_id': self._id,
                'registration': parent_registration._id
            },
            auth=Auth(self.initiated_by),
        )

        # TODO: Move this into the registration to be re-used in Forced Withdrawal
        # Remove any embargoes associated with the registration
        if parent_registration.embargo_end_date or parent_registration.is_pending_embargo:
            # Alter embargo state to make sure registration doesn't accidentally get published
            parent_registration.embargo.state = self.REJECTED
            parent_registration.embargo.approval_stage = (
                SanctionStates.MODERATOR_REJECTED if self.is_moderated
                else SanctionStates.REJECTED
            )

            parent_registration.registered_from.add_log(
                action=NodeLog.EMBARGO_CANCELLED,
                params={
                    'node': parent_registration.registered_from._id,
                    'registration': parent_registration._id,
                    'embargo_id': parent_registration.embargo._id,
                },
                auth=Auth(self.initiated_by),
            )
            parent_registration.embargo.save()

        # Ensure retracted registration is public
        # Pass auth=None because the registration initiator may not be
        # an admin on components (component admins had the opportunity
        # to disapprove the retraction by this point)
        for node in parent_registration.node_and_primary_descendants():
            node.set_privacy('public', auth=None, save=True, log=False)
            node.update_search()
        # force a save before sending data to share or retraction will not be updated
        self.save()

        if osf_settings.SHARE_ENABLED:
            update_share(parent_registration)

    def approve_retraction(self, user, token):
        '''Test function'''
        self.approve(user=user, token=token)

    def disapprove_retraction(self, user, token):
        '''Test function'''
        self.reject(user=user, token=token)


class RegistrationApproval(SanctionCallbackMixin, EmailApprovableSanction):
    SANCTION_TYPE = SanctionTypes.REGISTRATION_APPROVAL
    DISPLAY_NAME = 'Approval'
    SHORT_NAME = 'registration_approval'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_REGISTRATION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_REGISTRATION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'

    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)

    def _get_registration(self):
        return self.registrations.first()

    def _view_url_context(self, user_id, node):
        user_approval_state = self.approval_state.get(user_id, {})
        node_id = user_approval_state.get('node_id', node._id)
        return {
            'node_id': node_id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            registration = self._get_registration()
            node_id = user_approval_state.get('node_id', registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = self.approval_state.get(user_id, {}).get('rejection_token')
        if rejection_token:
            Registration = apps.get_model('osf.Registration')
            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Registration.load(node_id)
            return {
                'node_id': registration.registered_from._id,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        context = super(RegistrationApproval, self)._email_template_context(user, node, is_authorizer, urls)
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')

            approval_time_span = osf_settings.REGISTRATION_APPROVAL_TIME.days * 24

            registration = self._get_registration()

            context.update({
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
                'registration_link': registration_link,
                'approval_link': approval_link,
                'disapproval_link': disapproval_link,
                'approval_time_span': approval_time_span,
                'project_name': registration.title,
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
            })
        return context

    def _add_success_logs(self, node, user):
        NodeLog = apps.get_model('osf.NodeLog')

        src = node.registered_from
        src.add_log(
            action=NodeLog.PROJECT_REGISTERED,
            params={
                'parent_node': src.parent_node._id if src.parent_node else None,
                'node': src._primary_key,
                'registration': node._primary_key,
            },
            auth=Auth(user),
            save=False
        )
        src.save()

    def _on_complete(self, event_data):
        user = event_data.kwargs.get('user')
        if user is None and event_data.args:
            user = event_data.args[0]
        NodeLog = apps.get_model('osf.NodeLog')

        register = self._get_registration()
        if register.is_spammy:
            raise NodeStateError('Cannot approve a spammy registration')

        super()._on_complete(event_data)
        self.save()
        registered_from = register.registered_from
        # Pass auth=None because the registration initiator may not be
        # an admin on components (component admins had the opportunity
        # to disapprove the registration by this point)
        register.set_privacy('public', auth=None, log=False)
        for child in register.get_descendants_recursive(primary_only=True):
            child.set_privacy('public', auth=None, log=False)
        # Accounts for system actions where no `User` performs the final approval
        auth = Auth(user) if user else None
        registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_APPROVED,
            params={
                'node': registered_from._id,
                'registration': register._id,
                'registration_approval_id': self._id,
            },
            auth=auth,
        )
        for node in register.root.node_and_primary_descendants():
            self._add_success_logs(node, user)
            node.update_search()  # update search if public

        self.save()

    def _on_reject(self, event_data):
        user = event_data.kwargs.get('user')
        if user is None and event_data.args:
            user = event_data.args[0]
        NodeLog = apps.get_model('osf.NodeLog')

        registered_from = self.target_registration.registered_from
        self.target_registration.delete_registration_tree(save=True)
        registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_CANCELLED,
            params={
                'node': registered_from._id,
                'registration': self.target_registration._id,
                'registration_approval_id': self._id,
            },
            auth=Auth(user),
        )


class DraftRegistrationApproval(Sanction):

    SANCTION_TYPE = SanctionTypes.DRAFT_REGISTRATION_APPROVAL
    mode = Sanction.ANY

    # Since draft registrations that require approval are not immediately registered,
    # meta stores registration_choice and embargo_end_date (when applicable)
    meta = DateTimeAwareJSONField(default=dict, blank=True)

    def _send_rejection_email(self, user, draft):
        mails.send_mail(
            to_addr=user.username,
            mail=mails.DRAFT_REGISTRATION_REJECTED,
            user=user,
            osf_url=osf_settings.DOMAIN,
            provider=draft.provider,
            can_change_preferences=False,
            mimetype='html',
        )

    def approve(self, user):
        self.state = Sanction.APPROVED
        self._on_complete(user)

    def reject(self, user):
        self.state = Sanction.REJECTED
        self._on_reject(user)

    def _on_complete(self, user):
        DraftRegistration = apps.get_model('osf.DraftRegistration')

        draft = DraftRegistration.objects.get(approval=self)

        initiator = draft.initiator.merged_by or draft.initiator
        auth = Auth(initiator)
        registration = draft.register(auth=auth, save=True)
        registration_choice = self.meta['registration_choice']

        if registration_choice == 'immediate':
            sanction = functools.partial(registration.require_approval, initiator)
        elif registration_choice == 'embargo':
            embargo_end_date = parse_date(self.meta.get('embargo_end_date'))
            if not embargo_end_date.tzinfo:
                embargo_end_date = embargo_end_date.replace(tzinfo=pytz.UTC)
            sanction = functools.partial(
                registration.embargo_registration,
                initiator,
                embargo_end_date
            )
        else:
            raise ValueError("'registration_choice' must be either 'embargo' or 'immediate'")
        sanction(notify_initiator_on_complete=True)

    def _on_reject(self, user, *args, **kwargs):
        DraftRegistration = apps.get_model('osf.DraftRegistration')

        # clear out previous registration options
        self.meta = {}
        self.save()

        draft = DraftRegistration.objects.get(approval=self)
        initiator = draft.initiator.merged_by or draft.initiator
        self._send_rejection_email(initiator, draft)


class EmbargoTerminationApproval(EmailApprovableSanction):
    SANCTION_TYPE = SanctionTypes.EMBARGO_TERMINATION_APPROVAL
    DISPLAY_NAME = 'Embargo Termination Request'
    SHORT_NAME = 'embargo_termination_approval'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_TERMINATION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_TERMINATION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = osf_settings.DOMAIN + 'token_action/{node_id}/?token={token}'

    embargoed_registration = models.ForeignKey('Registration', null=True, blank=True, on_delete=models.CASCADE)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def is_moderated(self):
        return False  # Embargo Termination never requires Moderator Approval

    def _get_registration(self):
        return self.embargoed_registration

    def _view_url_context(self, user_id, node):
        registration = node or self._get_registration()
        return {
            'node_id': registration._id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            registration = self._get_registration()
            node_id = user_approval_state.get('node_id', registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = user_approval_state.get('rejection_token')
        if rejection_token:
            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            return {
                'node_id': node_id,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        context = super(EmbargoTerminationApproval, self)._email_template_context(
            user,
            node,
            is_authorizer=is_authorizer
        )
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = osf_settings.EMBARGO_TERMINATION_PENDING_TIME.days * 24

            registration = self._get_registration()

            context.update({
                'is_initiator': self.initiated_by == user,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),
                'initiated_by': self.initiated_by.fullname,
                'approval_link': approval_link,
                'project_name': registration.title,
                'disapproval_link': disapproval_link,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
                'approval_time_span': approval_time_span,
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'project_name': self.target_registration.title,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
                'is_moderated': self.is_moderated,
                'reviewable': self._get_registration(),

            })
        return context

    def _on_complete(self, event_data):
        super()._on_complete(event_data)
        self.target_registration.terminate_embargo(forced=True)

    def _on_reject(self, event_data):
        # Just forget this ever happened.
        self.target_registration.embargo_termination_approval = None
        self.target_registration.save()
