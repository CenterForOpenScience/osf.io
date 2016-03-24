import datetime
import functools
from dateutil.parser import parse as parse_date

from modularodm import (
    fields,
    Q,
)
from modularodm.exceptions import NoResultsFound
from modularodm.validators import MaxLengthValidator

from framework.auth import Auth
from framework.exceptions import PermissionsError
from framework.mongo import (
    ObjectId,
    StoredObject,
    validators,
)

from website import (
    mails,
    settings,
    tokens,
)
from website.exceptions import (
    InvalidSanctionApprovalToken,
    InvalidSanctionRejectionToken,
)
from website.prereg import utils as prereg_utils

VIEW_PROJECT_URL_TEMPLATE = settings.DOMAIN + '{node_id}/'

class Sanction(StoredObject):
    """Sanction class is a generic way to track approval states"""
    # Tell modularodm not to attach backends
    _meta = {
        'abstract': True,
    }

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    # Neither approved not cancelled
    UNAPPROVED = 'unapproved'
    # Has approval
    APPROVED = 'approved'
    # Rejected by at least one person
    REJECTED = 'rejected'
    # Embargo has been completed
    COMPLETED = 'completed'

    state = fields.StringField(
        default=UNAPPROVED,
        validate=validators.choice_in((
            UNAPPROVED,
            APPROVED,
            REJECTED,
            COMPLETED,
        ))
    )

    DISPLAY_NAME = 'Sanction'
    # SHORT_NAME must correspond with the associated foreign field to query against,
    # e.g. Node.find_one(Q(sanction.SHORT_NAME, 'eq', sanction))
    SHORT_NAME = 'sanction'

    APPROVAL_NOT_AUTHORIZED_MESSAGE = 'This user is not authorized to approve this {DISPLAY_NAME}'
    APPROVAL_INVALID_TOKEN_MESSAGE = 'Invalid approval token provided for this {DISPLAY_NAME}.'
    REJECTION_NOT_AUTHORIZED_MESSAEGE = 'This user is not authorized to reject this {DISPLAY_NAME}'
    REJECTION_INVALID_TOKEN_MESSAGE = 'Invalid rejection token provided for this {DISPLAY_NAME}.'

    # Controls whether or not the Sanction needs unanimous approval or just a single approval
    ANY = 'any'
    UNANIMOUS = 'unanimous'
    mode = UNANIMOUS

    initiation_date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    # Expiration date-- Sanctions in the UNAPPROVED state that are older than their end_date
    # are automatically made ACTIVE by a daily cron job
    # Use end_date=None for a non-expiring Sanction
    end_date = fields.DateTimeField(default=None)

    # Sanction subclasses must have an initiated_by field
    # initiated_by = fields.ForeignField('user', backref='initiated')

    # Expanded: Dictionary field mapping admin IDs their approval status and relevant tokens:
    # {
    #   'b3k97': {
    #     'has_approved': False,
    #     'approval_token': 'Pew7wj1Puf7DENUPFPnXSwa1rf3xPN',
    #     'rejection_token': 'TwozClTFOic2PYxHDStby94bCQMwJy'}
    # }
    approval_state = fields.DictionaryField()

    def __repr__(self):
        return '<Sanction(end_date={self.end_date!r}) with _id {self._id!r}>'.format(self=self)

    @property
    def is_pending_approval(self):
        return self.state == Sanction.UNAPPROVED

    @property
    def is_approved(self):
        return self.state == Sanction.APPROVED

    @property
    def is_rejected(self):
        return self.state == Sanction.REJECTED

    def approve(self, user):
        raise NotImplementedError("Sanction subclasses must implement an approve method.")

    def reject(self, user):
        raise NotImplementedError("Sanction subclasses must implement an approve method.")

    def _on_reject(self, user):
        """Callback for rejection of a Sanction

        :param User user:
        """
        raise NotImplementedError('Sanction subclasses must implement an #_on_reject method')

    def _on_complete(self, user):
        """Callback for when a Sanction has approval and enters the ACTIVE state

        :param User user:
        """
        raise NotImplementedError('Sanction subclasses must implement an #_on_complete method')

    def forcibly_reject(self):
        self.state = Sanction.REJECTED


class TokenApprovableSanction(Sanction):

    # Tell modularodm not to attach backends
    _meta = {
        'abstract': True,
    }

    def _validate_authorizer(self, user):
        """Subclasses may choose to provide extra restrictions on who can be an authorizer

        :return Boolean: True if user is allowed to be an authorizer else False
        """
        return True

    def add_authorizer(self, user, node, approved=False, save=False):
        """Add an admin user to this Sanction's approval state.

        :param User user: User to add.
        :param Node registration: The pending registration node.
        :param bool approved: Whether `user` has approved.
        :param bool save: Whether to save this object.
        """
        valid = self._validate_authorizer(user)
        if valid and user._id not in self.approval_state:
            self.approval_state[user._id] = {
                'has_approved': approved,
                'node_id': node._id,
                'approval_token': tokens.encode(
                    {
                        'user_id': user._id,
                        'sanction_id': self._id,
                        'action': 'approve_{}'.format(self.SHORT_NAME)
                    }
                ),
                'rejection_token': tokens.encode(
                    {
                        'user_id': user._id,
                        'sanction_id': self._id,
                        'action': 'reject_{}'.format(self.SHORT_NAME)
                    }
                ),
            }
            if save:
                self.save()
            return True
        return False

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

    def _on_approve(self, user, token):
        """Callback for when a single user approves a Sanction. Calls #_on_complete under two conditions:
        - mode is ANY and the Sanction has not already been cancelled
        - mode is UNANIMOUS and all users have given approval

        :param User user:
        :param str token: user's approval token
        """
        if self.mode == self.ANY or all(authorizer['has_approved'] for authorizer in self.approval_state.values()):
            self.state = Sanction.APPROVED
            self._on_complete(user)

    def token_for_user(self, user, method):
        """
        :param str method: 'approval' | 'rejection'
        """
        try:
            user_state = self.approval_state[user._id]
        except KeyError:
            raise PermissionsError(self.APPROVAL_NOT_AUTHORIZED_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        return user_state['{0}_token'.format(method)]

    def approve(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['approval_token'] != token:
                raise InvalidSanctionApprovalToken(self.APPROVAL_INVALID_TOKEN_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        except KeyError:
            raise PermissionsError(self.APPROVAL_NOT_AUTHORIZED_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        self.approval_state[user._id]['has_approved'] = True
        self._on_approve(user, token)

    def reject(self, user, token):
        """Cancels sanction if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['rejection_token'] != token:
                raise InvalidSanctionRejectionToken(self.REJECTION_INVALID_TOKEN_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        except KeyError:
            raise PermissionsError(self.REJECTION_NOT_AUTHORIZED_MESSAEGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        self.state = Sanction.REJECTED
        self._on_reject(user)

    def _notify_authorizer(self, user, node):
        pass

    def _notify_non_authorizer(self, user, node):
        pass

    def ask(self, group):
        """
        :param list group: List of (user, node) tuples containing contributors to notify about the
        sanction.
        """
        for contrib, node in group:
            if contrib._id in self.approval_state:
                self._notify_authorizer(contrib, node)
            else:
                self._notify_non_authorizer(contrib, node)


class EmailApprovableSanction(TokenApprovableSanction):

    # Tell modularodm not to attach backends
    _meta = {
        'abstract': True,
    }

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = None
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = None

    VIEW_URL_TEMPLATE = ''
    APPROVE_URL_TEMPLATE = ''
    REJECT_URL_TEMPLATE = ''

    # A flag to conditionally run a callback on complete
    notify_initiator_on_complete = fields.BooleanField(default=False)
    # Store a persistant copy of urls for use when needed outside of a request context.
    # This field gets automagically updated whenever models approval_state is modified
    # and the model is saved
    # {
    #   'abcde': {
    #     'approve': [APPROVAL_URL],
    #     'reject': [REJECT_URL],
    #   }
    # }
    stashed_urls = fields.DictionaryField(default=dict)

    @staticmethod
    def _format_or_empty(template, context):
        if context:
            return template.format(**context)
        return ''

    def _view_url(self, user_id, node):
        return self._format_or_empty(self.VIEW_URL_TEMPLATE, self._view_url_context(user_id, node))

    def _view_url_context(self, user_id, node):
        return None

    def _approval_url(self, user_id):
        return self._format_or_empty(self.APPROVE_URL_TEMPLATE, self._approval_url_context(user_id))

    def _approval_url_context(self, user_id):
        return None

    def _rejection_url(self, user_id):
        return self._format_or_empty(self.REJECT_URL_TEMPLATE, self._rejection_url_context(user_id))

    def _rejection_url_context(self, user_id):
        return None

    def _send_approval_request_email(self, user, template, context):
        mails.send_mail(
            user.username,
            template,
            user=user,
            **context
        )

    def _email_template_context(self, user, node, is_authorizer=False):
        return {}

    def _notify_authorizer(self, authorizer, node):
        context = self._email_template_context(authorizer, node, is_authorizer=True)
        if self.AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(authorizer, self.AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError

    def _notify_non_authorizer(self, user, node):
        context = self._email_template_context(user, node)
        if self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(user, self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError

    def add_authorizer(self, user, node, **kwargs):
        super(EmailApprovableSanction, self).add_authorizer(user, node, **kwargs)
        self.stashed_urls[user._id] = {
            'view': self._view_url(user._id, node),
            'approve': self._approval_url(user._id),
            'reject': self._rejection_url(user._id)
        }
        self.save()

    def _notify_initiator(self):
        raise NotImplementedError

    def _on_complete(self, *args):
        if self.notify_initiator_on_complete:
            self._notify_initiator()


class PreregCallbackMixin(object):

    def _notify_initiator(self):
        from website.project.model import DraftRegistration

        registration = self._get_registration()
        prereg_schema = prereg_utils.get_prereg_schema()

        draft = DraftRegistration.find_one(
            Q('registered_node', 'eq', registration)
        )

        if prereg_schema in registration.registered_schema:
            mails.send_mail(
                draft.initiator.username,
                mails.PREREG_CHALLENGE_ACCEPTED,
                user=draft.initiator,
                registration_url=registration.absolute_url,
                mimetype='html'
            )

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        registration = self._get_registration()
        prereg_schema = prereg_utils.get_prereg_schema()
        if prereg_schema in registration.registered_schema:
            return {
                'custom_message': ' as part of the Preregistration Challenge (https://cos.io/prereg)'
            }
        else:
            return {}

class Embargo(PreregCallbackMixin, EmailApprovableSanction):
    """Embargo object for registrations waiting to go public."""

    DISPLAY_NAME = 'Embargo'
    SHORT_NAME = 'embargo'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    initiated_by = fields.ForeignField('user', backref='embargoed')
    for_existing_registration = fields.BooleanField(default=False)

    @property
    def is_completed(self):
        return self.state == self.COMPLETED

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

    def __repr__(self):
        from website.project.model import Node

        parent_registration = None
        try:
            parent_registration = Node.find_one(Q('embargo', 'eq', self))
        except NoResultsFound:
            pass
        return ('<Embargo(parent_registration={0}, initiated_by={1}, '
                'end_date={2}) with _id {3}>').format(
            parent_registration,
            self.initiated_by,
            self.end_date,
            self._id
        )

    def _get_registration(self):
        from website.project.model import Node

        return Node.find_one(Q('embargo', 'eq', self))

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
            from website.project.model import Node

            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
            return {
                'node_id': registration.registered_from,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        context = super(Embargo, self)._email_template_context(user, node, is_authorizer, urls)
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = settings.EMBARGO_PENDING_TIME.days * 24

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
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
            })
        return context

    def _on_reject(self, user):
        from website.project.model import NodeLog

        parent_registration = self._get_registration()
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_CANCELLED,
            params={
                'node': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(user),
        )
        # Remove backref to parent project if embargo was for a new registration
        if not self.for_existing_registration:
            parent_registration.delete_registration_tree(save=True)
            parent_registration.registered_from = None
        # Delete parent registration if it was created at the time the embargo was initiated
        if not self.for_existing_registration:
            parent_registration.is_deleted = True
            parent_registration.save()

    def disapprove_embargo(self, user, token):
        """Cancels retraction if user is admin and token verifies."""
        self.reject(user, token)

    def _on_complete(self, user):
        from website.project.model import NodeLog

        super(Embargo, self)._on_complete(user)
        parent_registration = self._get_registration()
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_APPROVED,
            params={
                'node': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(self.initiated_by),
        )
        self.save()

    def approve_embargo(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        self.approve(user, token)


class Retraction(EmailApprovableSanction):
    """
    Retraction object for public registrations.
    Externally (specifically in user-facing language) retractions should be referred to as "Withdrawals", i.e.
    "Retract Registration" -> "Withdraw Registration", "Retracted" -> "Withdrawn", etc.
    """

    DISPLAY_NAME = 'Retraction'
    SHORT_NAME = 'retraction'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_RETRACTION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_RETRACTION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    initiated_by = fields.ForeignField('user', backref='initiated')
    justification = fields.StringField(default=None, validate=MaxLengthValidator(2048))

    def __repr__(self):
        from website.project.model import Node

        parent_registration = None
        try:
            parent_registration = Node.find_one(Q('retraction', 'eq', self))
        except NoResultsFound:
            pass
        return ('<Retraction(parent_registration={0}, initiated_by={1}) '
                'with _id {2}>').format(
            parent_registration,
            self.initiated_by,
            self._id
        )

    def _view_url_context(self, user_id, node):
        from website.project.model import Node

        registration = Node.find_one(Q('retraction', 'eq', self))
        return {
            'node_id': registration._id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            from website.project.model import Node

            root_registration = Node.find_one(Q('retraction', 'eq', self))
            node_id = user_approval_state.get('node_id', root_registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = user_approval_state.get('rejection_token')
        if rejection_token:
            from website.project.model import Node

            root_registration = Node.find_one(Q('retraction', 'eq', self))
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
            return {
                'node_id': registration.registered_from._id,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            from website.project.model import Node

            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = settings.RETRACTION_PENDING_TIME.days * 24

            registration = Node.find_one(Q('retraction', 'eq', self))

            return {
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
                'project_name': registration.title,
                'registration_link': registration_link,
                'approval_link': approval_link,
                'disapproval_link': disapproval_link,
                'approval_time_span': approval_time_span,
            }
        else:
            return {
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
            }

    def _on_reject(self, user):
        from website.project.model import Node, NodeLog

        parent_registration = Node.find_one(Q('retraction', 'eq', self))
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_CANCELLED,
            params={
                'node': parent_registration._id,
                'retraction_id': self._id,
            },
            auth=Auth(user),
            save=True,
        )

    def _on_complete(self, user):
        from website.project.model import Node, NodeLog

        parent_registration = Node.find_one(Q('retraction', 'eq', self))
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_APPROVED,
            params={
                'node': parent_registration._id,
                'retraction_id': self._id,
            },
            auth=Auth(self.initiated_by),
        )
        # Remove any embargoes associated with the registration
        if parent_registration.embargo_end_date or parent_registration.is_pending_embargo:
            parent_registration.embargo.state = self.REJECTED
            parent_registration.registered_from.add_log(
                action=NodeLog.EMBARGO_CANCELLED,
                params={
                    'node': parent_registration._id,
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

    def approve_retraction(self, user, token):
        self.approve(user, token)

    def disapprove_retraction(self, user, token):
        self.reject(user, token)


class RegistrationApproval(PreregCallbackMixin, EmailApprovableSanction):

    DISPLAY_NAME = 'Approval'
    SHORT_NAME = 'registration_approval'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_REGISTRATION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_REGISTRATION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    initiated_by = fields.ForeignField('user', backref='registration_approved')

    def _get_registration(self):
        from website.project.model import Node

        return Node.find_one(Q('registration_approval', 'eq', self))

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
            from website.project.model import Node

            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
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

            approval_time_span = settings.REGISTRATION_APPROVAL_TIME.days * 24

            registration = self._get_registration()

            context.update({
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
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
            })
        return context

    def _add_success_logs(self, node, user):
        from website.project.model import NodeLog

        src = node.registered_from
        src.add_log(
            action=NodeLog.PROJECT_REGISTERED,
            params={
                'parent_node': src.parent_id,
                'node': src._primary_key,
                'registration': node._primary_key,
            },
            auth=Auth(user),
            save=False
        )
        src.save()

    def _on_complete(self, user):
        from website.project.model import NodeLog

        super(RegistrationApproval, self)._on_complete(user)
        self.state = Sanction.APPROVED
        register = self._get_registration()
        registered_from = register.registered_from
        # Pass auth=None because the registration initiator may not be
        # an admin on components (component admins had the opportunity
        # to disapprove the registration by this point)
        register.set_privacy('public', auth=None, log=False)
        for child in register.get_descendants_recursive(lambda n: n.primary):
            child.set_privacy('public', auth=None, log=False)
        # Accounts for system actions where no `User` performs the final approval
        auth = Auth(user) if user else None
        registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_APPROVED,
            params={
                'node': registered_from._id,
                'registration_approval_id': self._id,
            },
            auth=auth,
        )
        for node in register.root.node_and_primary_descendants():
            self._add_success_logs(node, user)
            node.update_search()  # update search if public

        self.save()

    def _on_reject(self, user):
        from website.project.model import NodeLog

        register = self._get_registration()
        registered_from = register.registered_from
        register.delete_registration_tree(save=True)
        registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_CANCELLED,
            params={
                'node': register._id,
                'registration_approval_id': self._id,
            },
            auth=Auth(user),
        )

class AlternativeCitation(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    name = fields.StringField(required=True, validate=MaxLengthValidator(256))
    text = fields.StringField(required=True, validate=MaxLengthValidator(2048))

    def to_json(self):
        return {
            "id": self._id,
            "name": self.name,
            "text": self.text
        }

class DraftRegistrationApproval(Sanction):

    mode = Sanction.ANY

    # Since draft registrations that require approval are not immediately registered,
    # meta stores registration_choice and embargo_end_date (when applicable)
    meta = fields.DictionaryField(default=dict)

    def _send_rejection_email(self, user, draft):
        schema = draft.registration_schema
        prereg_schema = prereg_utils.get_prereg_schema()

        if schema._id == prereg_schema._id:
            mails.send_mail(
                user.username,
                mails.PREREG_CHALLENGE_REJECTED,
                user=user,
                draft_url=draft.absolute_url
            )
        else:
            raise NotImplementedError(
                'TODO: add a generic email template for registration approvals'
            )

    def approve(self, user):
        if settings.PREREG_ADMIN_TAG not in user.system_tags:
            raise PermissionsError("This user does not have permission to approve this draft.")
        self.state = Sanction.APPROVED
        self._on_complete(user)

    def reject(self, user):
        if settings.PREREG_ADMIN_TAG not in user.system_tags:
            raise PermissionsError("This user does not have permission to approve this draft.")
        self.state = Sanction.REJECTED
        self._on_reject(user)

    def _on_complete(self, user):
        from website.project.model import DraftRegistration

        draft = DraftRegistration.find_one(
            Q('approval', 'eq', self)
        )
        auth = Auth(draft.initiator)
        registration = draft.register(
            auth=auth,
            save=True
        )
        registration_choice = self.meta['registration_choice']

        if registration_choice == 'immediate':
            sanction = functools.partial(registration.require_approval, draft.initiator)
        elif registration_choice == 'embargo':
            sanction = functools.partial(
                registration.embargo_registration,
                draft.initiator,
                parse_date(self.meta.get('embargo_end_date'), ignoretz=True)
            )
        else:
            raise ValueError("'registration_choice' must be either 'embargo' or 'immediate'")
        sanction(notify_initiator_on_complete=True)

    def _on_reject(self, user, *args, **kwargs):
        from website.project.model import DraftRegistration

        # clear out previous registration options
        self.meta = {}
        self.save()

        draft = DraftRegistration.find_one(
            Q('approval', 'eq', self)
        )
        self._send_rejection_email(draft.initiator, draft)

class EmbargoTerminationApproval(EmailApprovableSanction):

    DISPLAY_NAME = 'Embargo Termination Request'
    SHORT_NAME = 'embargo-termination-approval'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_TERMINATION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_TERMINATION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    embargoed_registration = fields.FloatField('node')

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
            from website.project.model import Node

            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
            return {
                'node_id': registration.registered_from,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        context = super(EmbargoTerminationApproval, self)._email_template_context(user, node, is_authorizer, urls)
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = settings.EMBARGO_PENDING_TIME.days * 24

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
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
            })
        return context

    def _on_reject(self, user):
        from website.project.model import NodeLog

        registration = self._get_registration()
        registration.registered_from.add_log(
            action=NodeLog.EMBARGO_TERMINATION_CANCELLED,
            params={
                'node': registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(user),
        )
        self.save()

    def _on_complete(self, user):
        from website.project.model import NodeLog

        super(EmbargoTerminationApproval, self)._on_complete(user)
        registration = self._get_registration()
        registration.registered_from.add_log(
            action=NodeLog.EMBARGO_TERMINATION_APPROVED,
            params={
                'node': registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(self.initiated_by),
        )
        self.save()
