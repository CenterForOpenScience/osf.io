from framework.exceptions import PermissionsError
from osf_models.models import MetaSchema
from osf_models.models.base import BaseModel
from osf_models.utils.base import get_object_id
from django.db import models
from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField
from website import (tokens, settings, mails)
from website.exceptions import InvalidSanctionRejectionToken, InvalidSanctionApprovalToken

VIEW_PROJECT_URL_TEMPLATE = settings.DOMAIN + '{node_id}/'


class PreregCallbackMixin(object):
    pass


class Sanction(BaseModel):
    """Sanction class is a generic way to track approval states"""

    # Neither approved not cancelled
    UNAPPROVED = 'unapproved'
    # Has approval
    APPROVED = 'approved'
    # Rejected by at least one person
    REJECTED = 'rejected'
    # Embargo has been completed
    COMPLETED = 'completed'

    STATE_CHOICES = ((UNAPPROVED, UNAPPROVED.title()),
                     (APPROVED, APPROVED.title()),
                     (REJECTED, REJECTED.title()),
                     (COMPLETED, COMPLETED.title()), )

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

    # Sanction subclasses must have an initiated_by field
    # initiated_by = fields.ForeignField('user', backref='initiated')

    # Expanded: Dictionary field mapping admin IDs their approval status and relevant tokens:
    # {
    #   'b3k97': {
    #     'has_approved': False,
    #     'approval_token': 'Pew7wj1Puf7DENUPFPnXSwa1rf3xPN',
    #     'rejection_token': 'TwozClTFOic2PYxHDStby94bCQMwJy'}
    # }
    approval_state = DatetimeAwareJSONField(default={})

    # Expiration date-- Sanctions in the UNAPPROVED state that are older than their end_date
    # are automatically made ACTIVE by a daily cron job
    # Use end_date=None for a non-expiring Sanction
    end_date = models.DateTimeField(null=True, default=None)
    guid = models.CharField(max_length=255, default=get_object_id)
    initiation_date = models.DateTimeField(null=True)  # auto_now=True)

    state = models.CharField(choices=STATE_CHOICES,
                             default=UNAPPROVED,
                             max_length=255)

    @property
    def _id(self):
        return self.guid

    def __repr__(self):
        return '<Sanction(end_date={self.end_date!r}) with _id {self._id!r}>'.format(
            self=self)

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
        raise NotImplementedError(
            "Sanction subclasses must implement an approve method.")

    def reject(self, user):
        raise NotImplementedError(
            "Sanction subclasses must implement an approve method.")

    def _on_reject(self, user):
        """Callback for rejection of a Sanction

        :param User user:
        """
        raise NotImplementedError(
            'Sanction subclasses must implement an #_on_reject method')

    def _on_complete(self, user):
        """Callback for when a Sanction has approval and enters the ACTIVE state

        :param User user:
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
                'approval_token': tokens.encode({
                    'user_id': user._id,
                    'sanction_id': self._id,
                    'action': 'approve_{}'.format(self.SHORT_NAME)
                }),
                'rejection_token': tokens.encode({
                    'user_id': user._id,
                    'sanction_id': self._id,
                    'action': 'reject_{}'.format(self.SHORT_NAME)
                }),
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
        if self.mode == self.ANY or all(
                authorizer['has_approved']
                for authorizer in self.approval_state.values()):
            self.state = Sanction.APPROVED
            self._on_complete(user)

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

    def approve(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['approval_token'] != token:
                raise InvalidSanctionApprovalToken(
                    self.APPROVAL_INVALID_TOKEN_MESSAGE.format(
                        DISPLAY_NAME=self.DISPLAY_NAME))
        except KeyError:
            raise PermissionsError(self.APPROVAL_NOT_AUTHORIZED_MESSAGE.format(
                DISPLAY_NAME=self.DISPLAY_NAME))
        self.approval_state[user._id]['has_approved'] = True
        self._on_approve(user, token)

    def reject(self, user, token):
        """Cancels sanction if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['rejection_token'] != token:
                raise InvalidSanctionRejectionToken(
                    self.REJECTION_INVALID_TOKEN_MESSAGE.format(
                        DISPLAY_NAME=self.DISPLAY_NAME))
        except KeyError:
            raise PermissionsError(
                self.REJECTION_NOT_AUTHORIZED_MESSAEGE.format(
                    DISPLAY_NAME=self.DISPLAY_NAME))
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
    stashed_urls = DatetimeAwareJSONField(default={})

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
        mails.send_mail(user.username, template, user=user, **context)

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
            raise NotImplementedError

    def _notify_non_authorizer(self, user, node):
        context = self._email_template_context(user, node)
        if self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(
                user, self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError

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

    def _on_complete(self, *args):
        if self.notify_initiator_on_complete:
            self._notify_initiator()

    class Meta:
        abstract = True


class PreregCallbackMixin(object):
    def _notify_initiator(self):
        from osf_models.models import DraftRegistration

        registration = self._get_registration()
        prereg_schema = MetaSchema.get_prereg_schema()

        draft = DraftRegistration.objects.get(registered_node=registration)

        if prereg_schema in registration.registered_schema:
            mails.send_mail(draft.initiator.username,
                            mails.PREREG_CHALLENGE_ACCEPTED,
                            user=draft.initiator,
                            registration_url=registration.absolute_url,
                            mimetype='html')

    def _email_template_context(self,
                                user,
                                node,
                                is_authorizer=False,
                                urls=None):
        registration = self._get_registration()
        prereg_schema = MetaSchema.get_prereg_schema()
        if prereg_schema in registration.registered_schema:
            return {
                'custom_message':
                ' as part of the Preregistration Challenge (https://cos.io/prereg)'
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

    initiated_by = models.ForeignKey('User', null=True)
    for_existing_registration = models.BooleanField(default=False)

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
        pass
        # from osf_models.models import Node
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
        from website.project.model import Node

        return Node.find_one(Q('embargo', 'eq', self))

    def _view_url_context(self, user_id, node):
        registration = node or self._get_registration()
        return {'node_id': registration._id}

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            registration = self._get_registration()
            node_id = user_approval_state.get('node_id', registration._id)
            return {'node_id': node_id, 'token': approval_token, }

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
                'node': parent_registration.registered_from_id,
                'registration': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(user), )
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
                'node': parent_registration.registered_from_id,
                'registration': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(self.initiated_by), )
        self.save()

    def approve_embargo(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        self.approve(user, token)

    def mark_as_completed(self):
        self.state = Sanction.COMPLETED
        self.save()


class RegistrationApproval(PreregCallbackMixin, EmailApprovableSanction):
    pass
