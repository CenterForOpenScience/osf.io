import logging
import datetime
import html
from future.moves.urllib.parse import urljoin

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from guardian.models import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from dirtyfields import DirtyFieldsMixin

from framework.auth import Auth
from framework.exceptions import PermissionsError
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.permissions import ADMIN, READ, WRITE
from osf.exceptions import NodeStateError, DraftRegistrationStateError
from website.util import api_v2_url
from website import settings
from website.archiver import ARCHIVER_INITIATED

from osf.metrics import RegistriesModerationMetrics
from osf.models import (
    Embargo,
    EmbargoTerminationApproval,
    DraftRegistrationApproval,
    DraftRegistrationContributor,
    Node,
    OSFUser,
    RegistrationApproval,
    RegistrationSchema,
    Retraction,
)

from osf.models.action import RegistrationAction
from osf.models.archive import ArchiveJob
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.draft_node import DraftNode
from osf.models.node import AbstractNode
from osf.models.mixins import (
    EditableFieldsMixin,
    Loggable,
    GuardianMixin,
)
from osf.models.nodelog import NodeLog
from osf.models.provider import RegistrationProvider
from osf.models.mixins import RegistrationResponseMixin
from osf.models.tag import Tag
from osf.models.validators import validate_title
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.workflows import (
    RegistrationModerationStates,
    RegistrationModerationTriggers,
    SanctionStates,
    SanctionTypes
)

import osf.utils.notifications as notify

logger = logging.getLogger(__name__)


class Registration(AbstractNode):

    WRITABLE_WHITELIST = [
        'article_doi',
        'description',
        'is_public',
        'node_license',
        'category',
    ]
    provider = models.ForeignKey(
        'RegistrationProvider',
        related_name='registrations',
        null=True,
        on_delete=models.SET_NULL
    )
    registered_date = NonNaiveDateTimeField(db_index=True, null=True, blank=True)

    # This is a NullBooleanField because of inheritance issues with using a BooleanField
    # TODO: Update to BooleanField(default=False, null=True) when Django is updated to >=2.1
    external_registration = models.NullBooleanField(default=False)
    registered_user = models.ForeignKey(OSFUser,
                                        related_name='related_to',
                                        on_delete=models.SET_NULL,
                                        null=True, blank=True)

    # TODO: Consider making this a FK, as there can be one per Registration
    registered_schema = models.ManyToManyField(RegistrationSchema)

    registered_meta = DateTimeAwareJSONField(default=dict, blank=True)
    registered_from = models.ForeignKey('self',
                                        related_name='registrations',
                                        on_delete=models.SET_NULL,
                                        null=True, blank=True)
    # Sanctions
    registration_approval = models.ForeignKey('RegistrationApproval',
                                            related_name='registrations',
                                            null=True, blank=True,
                                            on_delete=models.SET_NULL)
    retraction = models.ForeignKey('Retraction',
                                related_name='registrations',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    embargo = models.ForeignKey('Embargo',
                                related_name='registrations',
                                null=True, blank=True,
                                on_delete=models.SET_NULL)
    embargo_termination_approval = models.ForeignKey('EmbargoTerminationApproval',
                                                    related_name='registrations',
                                                    null=True, blank=True,
                                                    on_delete=models.SET_NULL)
    files_count = models.PositiveIntegerField(blank=True, null=True)

    moderation_state = models.CharField(
        max_length=30,
        choices=RegistrationModerationStates.char_field_choices(),
        default=RegistrationModerationStates.INITIAL.db_name
    )

    @staticmethod
    def find_failed_registrations():
        expired_if_before = timezone.now() - settings.ARCHIVE_TIMEOUT_TIMEDELTA
        node_id_list = ArchiveJob.objects.filter(sent=False, datetime_initiated__lt=expired_if_before, status=ARCHIVER_INITIATED).values_list('dst_node', flat=True)
        root_nodes_id = AbstractNode.objects.filter(id__in=node_id_list).values_list('root', flat=True).distinct()
        stuck_regs = AbstractNode.objects.filter(id__in=root_nodes_id, is_deleted=False)
        return stuck_regs

    @property
    def registration_schema(self):
        # For use in RegistrationResponseMixin
        if self.registered_schema.exists():
            return self.registered_schema.first()
        return None

    def get_registration_metadata(self, schema):
        # Overrides RegistrationResponseMixin
        registered_meta = self.registered_meta or {}
        return registered_meta.get(schema._id, None)

    @property
    def file_storage_resource(self):
        # Overrides RegistrationResponseMixin
        return self.registered_from

    @property
    def registered_schema_id(self):
        schema = self.registration_schema
        return schema._id if schema else None

    @property
    def is_registration(self):
        """For v1 compat."""
        return True

    @property
    def is_stuck_registration(self):
        return self in self.find_failed_registrations()

    @property
    def is_collection(self):
        """For v1 compat."""
        return False

    @property
    def archive_job(self):
        return self.archive_jobs.first() if self.archive_jobs.count() else None

    @property
    def sanction(self):
        root = self._dirty_root
        sanction = (
            root.retraction or
            root.embargo_termination_approval or
            root.embargo or
            root.registration_approval
        )
        if sanction:
            return sanction
        else:
            return None

    @property
    def is_registration_approved(self):
        root = self._dirty_root
        if root.registration_approval is None:
            return False
        return root.registration_approval.is_approved

    @property
    def is_pending_embargo(self):
        root = self._dirty_root
        if root.embargo is None:
            return False
        return root.embargo.is_pending_approval

    @property
    def is_pending_embargo_for_existing_registration(self):
        """ Returns True if Node has an Embargo pending approval for an
        existing registrations. This is used specifically to ensure
        registrations pre-dating the Embargo feature do not get deleted if
        their respective Embargo request is rejected.
        """
        root = self._dirty_root
        if root.embargo is None:
            return False
        return root.embargo.pending_registration

    @property
    def is_retracted(self):
        root = self._dirty_root
        if root.retraction is None:
            return False
        return root.retraction.is_approved

    @property
    def is_pending_registration(self):
        root = self._dirty_root
        if root.registration_approval is None:
            return False
        return root.registration_approval.is_pending_approval

    @property
    def is_pending_retraction(self):
        root = self._dirty_root
        if root.retraction is None:
            return False
        return root.retraction.is_pending_approval

    @property
    def is_pending_embargo_termination(self):
        root = self._dirty_root
        if root.embargo_termination_approval is None:
            return False
        return root.embargo_termination_approval.is_pending_approval

    @property
    def is_embargoed(self):
        """A Node is embargoed if:
        - it has an associated Embargo record
        - that record has been approved
        - the node is not public (embargo not yet lifted)
        """
        root = self._dirty_root
        if root.is_public or root.embargo is None:
            return False
        return root.embargo.is_approved

    @property
    def embargo_end_date(self):
        root = self._dirty_root
        if root.embargo is None:
            return False
        return root.embargo.embargo_end_date

    @property
    def archiving(self):
        job = self.archive_job
        return job and not job.done and not job.archive_tree_finished()

    @property
    def is_moderated(self):
        if not self.provider:
            return False
        return self.provider.is_reviewed

    @property
    def _dirty_root(self):
        """Equivalent to `self.root`, but don't let Django fetch a clean copy
        when `self == self.root`. Use when it's important to reflect unsaved
        state rather than database state.
        """
        if self.id == self.root_id:
            return self
        return self.root

    def date_withdrawn(self):
        return getattr(self.root.retraction, 'date_retracted', None)

    @property
    def withdrawal_justification(self):
        return getattr(self.root.retraction, 'justification', None)

    def can_view(self, auth):
        if super().can_view(auth):
            return True

        if not auth or not auth.user or not self.is_moderated:
            return False

        moderator_viewable_states = {
            RegistrationModerationStates.PENDING.db_name,
            RegistrationModerationStates.PENDING_WITHDRAW.db_name,
            RegistrationModerationStates.EMBARGO.db_name,
            RegistrationModerationStates.PENDING_EMBARGO_TERMINATION.db_name,
        }
        user_is_moderator = auth.user.has_perm('view_submissions', self.provider)
        if self.moderation_state in moderator_viewable_states and user_is_moderator:
            return True

        return False

    def _initiate_approval(self, user, notify_initiator_on_complete=False):
        end_date = timezone.now() + settings.REGISTRATION_APPROVAL_TIME
        self.registration_approval = RegistrationApproval.objects.create(
            initiated_by=user,
            end_date=end_date,
            notify_initiator_on_complete=notify_initiator_on_complete
        )
        self.save()  # Set foreign field reference Node.registration_approval
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            self.registration_approval.add_authorizer(admin, node=node)
        self.registration_approval.save()  # Save approval's approval_state
        return self.registration_approval

    def require_approval(self, user, notify_initiator_on_complete=False):
        if not self.is_registration:
            raise NodeStateError('Only registrations can require registration approval')
        if not self.is_admin_contributor(user):
            raise PermissionsError('Only admins can initiate a registration approval')

        approval = self._initiate_approval(user, notify_initiator_on_complete)

        self.registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_INITIATED,
            params={
                'node': self.registered_from._id,
                'registration': self._id,
                'registration_approval_id': approval._id,
            },
            auth=Auth(user),
            save=True,
        )
        self.update_moderation_state()

    def _initiate_embargo(self, user, end_date, for_existing_registration=False,
                          notify_initiator_on_complete=False):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param end_date: Date when the registration should be made public
        """
        end_date_midnight = datetime.datetime.combine(
            end_date,
            datetime.datetime.min.time()
        ).replace(tzinfo=end_date.tzinfo)
        self.embargo = Embargo.objects.create(
            initiated_by=user,
            end_date=end_date_midnight,
            for_existing_registration=for_existing_registration,
            notify_initiator_on_complete=notify_initiator_on_complete
        )
        self.update_moderation_state()
        self.save()  # Set foreign field reference Node.embargo
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            self.embargo.add_authorizer(admin, node)
        self.embargo.save()  # Save embargo's approval_state
        return self.embargo

    def embargo_registration(self, user, end_date, for_existing_registration=False,
                             notify_initiator_on_complete=False):
        """Enter registration into an embargo period at end of which, it will
        be made public
        :param user: User initiating the embargo
        :param end_date: Date when the registration should be made public
        :raises: NodeStateError if Node is not a registration
        :raises: PermissionsError if user is not an admin for the Node
        :raises: ValidationError if end_date is not within time constraints
        """
        if not self.is_admin_contributor(user) and not user.has_perm('accept_submissions', self.provider):
            raise PermissionsError('Only admins may embargo a registration')
        if not self._is_embargo_date_valid(end_date):
            if (end_date - timezone.now()) >= settings.EMBARGO_END_DATE_MIN:
                raise ValidationError('Registrations can only be embargoed for up to four years.')
            raise ValidationError('Embargo end date must be at least three days in the future.')

        self.embargo = self._initiate_embargo(user, end_date,
                                         for_existing_registration=for_existing_registration,
                                         notify_initiator_on_complete=notify_initiator_on_complete)

        self.registered_from.add_log(
            action=NodeLog.EMBARGO_INITIATED,
            params={
                'node': self.registered_from._id,
                'registration': self._id,
                'embargo_id': self.embargo._id,
            },
            auth=Auth(user),
            save=True,
        )
        if self.is_public:
            self.set_privacy('private', Auth(user))

    def request_embargo_termination(self, user):
        """Initiates an EmbargoTerminationApproval to lift this Embargoed Registration's
        embargo early."""
        if not self.is_embargoed:
            raise NodeStateError('This node is not under active embargo')
        if not self.root == self:
            raise NodeStateError('Only the root of an embargoed registration can request termination')

        approval = EmbargoTerminationApproval(
            initiated_by=user,
            embargoed_registration=self,
        )
        admins = [admin for admin in self.root.get_admin_contributors_recursive(unique_users=True)]
        for (admin, node) in admins:
            approval.add_authorizer(admin, node=node)
        approval.save()
        approval.ask(admins)
        self.embargo_termination_approval = approval
        self.update_moderation_state()
        self.save()
        return approval

    def terminate_embargo(self, forced=False):
        """Handles the completion of an Embargoed registration.
        Adds a log to the registered_from Node.

        :param bool forced: False if the embargo is expiring,
                            True if the embargo is being terminated early

        """
        if not self.is_embargoed:
            raise NodeStateError('This node is not under active embargo')

        action = NodeLog.EMBARGO_COMPLETED if not forced else NodeLog.EMBARGO_TERMINATED
        self.registered_from.add_log(
            action=action,
            params={
                'project': self._id,
                'node': self.registered_from._id,
                'registration': self._id,
            },
            auth=None,
            save=True
        )
        self.embargo.mark_as_completed()
        for node in self.node_and_primary_descendants():
            node.set_privacy(
                self.PUBLIC,
                auth=None,
                log=False,
                save=True
            )
        return True

    def get_contributor_registration_response_keys(self):
        """
        Returns the keys of the supplemental responses whose answers
        contain author information
        :returns QuerySet
        """
        return self.registration_schema.schema_blocks.filter(
            block_type='contributors-input', registration_response_key__isnull=False,
        ).values_list('registration_response_key', flat=True)

    def copy_registered_meta_and_registration_responses(self, draft, save=True):
        """
        Sets the registration's registered_meta and registration_responses from the draft.

        If contributor information is in a question, build an accurate bibliographic
        contributors list on the registration
        """
        if not self.registered_meta:
            self.registered_meta = {}

        registration_metadata = draft.registration_metadata
        registration_responses = draft.registration_responses

        bibliographic_contributors = ', '.join(
            draft.branched_from.visible_contributors.values_list('fullname', flat=True)
        )
        contributor_keys = self.get_contributor_registration_response_keys()

        for key in contributor_keys:
            if key in registration_metadata:
                registration_metadata[key]['value'] = bibliographic_contributors
            if key in registration_responses:
                registration_responses[key] = bibliographic_contributors

        self.registered_meta[self.registration_schema._id] = registration_metadata
        self.registration_responses = registration_responses

        if save:
            self.save()

    def _initiate_retraction(self, user, justification=None, moderator_initiated=False):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param justification: Justification, if given, for retraction
        """
        self.retraction = Retraction.objects.create(
            initiated_by=user,
            justification=justification or None,  # make empty strings None
            state=Retraction.UNAPPROVED,
        )
        self.save()
        if not moderator_initiated:
            admins = self.get_admin_contributors_recursive(unique_users=True)
            for (admin, node) in admins:
                self.retraction.add_authorizer(admin, node)
        self.retraction.save()  # Save retraction approval state
        return self.retraction

    def retract_registration(self, user, justification=None, save=True, moderator_initiated=False):
        """Retract public registration. Instantiate new Retraction object
        and associate it with the respective registration.
        """

        if not self.is_public and not (self.embargo_end_date or self.is_pending_embargo):
            raise NodeStateError('Only public or embargoed registrations may be withdrawn.')

        if self.root_id != self.id:
            raise NodeStateError('Withdrawal of non-parent registrations is not permitted.')

        if moderator_initiated:
            justification = 'Force withdrawn by moderator: ' + justification
            if not self.is_moderated:
                raise ValueError('Forced retraction is only supported for moderated registrations.')
            if not user.has_perm('withdraw_submissions', self.provider):
                raise PermissionsError(
                    f'User {user} does not have moderator privileges on Provider {self.provider}')

        retraction = self._initiate_retraction(
            user, justification, moderator_initiated=moderator_initiated)
        self.retraction = retraction
        self.registered_from.add_log(
            action=NodeLog.RETRACTION_INITIATED,
            params={
                'node': self.registered_from._id,
                'registration': self._id,
                'retraction_id': retraction._id,
            },
            auth=Auth(user),
        )

        # Automatically accept moderator_initiated retractions
        if moderator_initiated:
            self.retraction.approval_stage = SanctionStates.PENDING_MODERATION
            self.retraction.accept(user=user, comment=justification)
            self.refresh_from_db()  # grab updated state

        if save:
            self.update_moderation_state()
            self.save()

        return retraction

    def delete_registration_tree(self, save=False):
        logger.debug('Marking registration {} as deleted'.format(self._id))
        self.is_deleted = True
        self.deleted = timezone.now()
        for draft_registration in DraftRegistration.objects.filter(registered_node=self):
            # Allow draft registration to be submitted
            if draft_registration.approval:
                draft_registration.approval = None
                draft_registration.save()
        if not getattr(self.embargo, 'for_existing_registration', False):
            self.registered_from = None
        if save:
            self.save()
        self.update_search()
        for child in self.nodes_primary:
            child.delete_registration_tree(save=save)

    def update_files_count(self):
        # Updates registration files_count at archival success or
        # at the end of forced (manual) archive for restarted (stuck or failed) registrations.
        field = AbstractNode._meta.get_field('modified')
        field.auto_now = False
        self.files_count = self.files.filter(deleted_on__isnull=True).count()
        self.save()
        field.auto_now = True

    def update_moderation_state(self, initiated_by=None, comment=''):
        '''Derive the RegistrationModerationState from the state of the active sanction.

        :param models.User initiated_by: The user who initiated the state change;
                used in reporting actions.
        :param str comment: Any comment moderator comment associated with the state change;
                used in reporting Actions.
        '''
        from_state = RegistrationModerationStates.from_db_name(self.moderation_state)

        active_sanction = self.sanction
        if active_sanction is None:  # Registration is ACCEPTED if there are no active sanctions.
            to_state = RegistrationModerationStates.ACCEPTED
        else:
            to_state = RegistrationModerationStates.from_sanction(active_sanction)

        if to_state is RegistrationModerationStates.UNDEFINED:
            # An UNDEFINED state is expected from a rejected retraction.
            # In other cases, report the error.
            if active_sanction.SANCTION_TYPE is not SanctionTypes.RETRACTION:
                logger.warning(
                    'Could not update moderation state from unsupported sanction/state '
                    'combination {sanction}.{state}'.format(
                        sanction=active_sanction.SANCTION_TYPE,
                        state=active_sanction.approval_stage.name)
                )
            # Use other underlying sanctions to compute the state
            if self.embargo:
                to_state = RegistrationModerationStates.from_sanction(self.embargo)
            elif self.registration_approval:
                to_state = RegistrationModerationStates.from_sanction(self.registration_approval)
            else:
                to_state = RegistrationModerationStates.ACCEPTED

        self._write_registration_action(from_state, to_state, initiated_by, comment)
        self.moderation_state = to_state.db_name
        self.save()

    def _write_registration_action(self, from_state, to_state, initiated_by, comment):
        '''Write a new RegistrationAction on relevant state transitions.'''
        trigger = RegistrationModerationTriggers.from_transition(from_state, to_state)
        if trigger is None:
            return  # Not a moderated event, no need to write an action

        initiated_by = initiated_by or self.sanction.initiated_by

        if not comment and trigger is RegistrationModerationTriggers.REQUEST_WITHDRAWAL:
            comment = self.withdrawal_justification or ''  # Withdrawal justification is null by default

        action = RegistrationAction.objects.create(
            target=self,
            creator=initiated_by,
            trigger=trigger.db_name,
            from_state=from_state.db_name,
            to_state=to_state.db_name,
            comment=comment
        )
        action.save()
        RegistriesModerationMetrics.record_transitions(action)

        moderation_notifications = {
            RegistrationModerationTriggers.SUBMIT: notify.notify_submit,
            RegistrationModerationTriggers.ACCEPT_SUBMISSION: notify.notify_accept_reject,
            RegistrationModerationTriggers.REJECT_SUBMISSION: notify.notify_accept_reject,
            RegistrationModerationTriggers.REQUEST_WITHDRAWAL: notify.notify_moderator_registration_requests_withdrawal,
            RegistrationModerationTriggers.REJECT_WITHDRAWAL: notify.notify_reject_withdraw_request,
            RegistrationModerationTriggers.ACCEPT_WITHDRAWAL: notify.notify_withdraw_registration,
            RegistrationModerationTriggers.FORCE_WITHDRAW: notify.notify_withdraw_registration,
        }

        notification = moderation_notifications.get(trigger)
        if notification:
            notification(
                resource=self,
                user=initiated_by,
                action=action,
                states=RegistrationModerationStates
            )

    def add_tag(self, tag, auth=None, save=True, log=True, system=False):
        if self.retraction is None:
            super(Registration, self).add_tag(tag, auth, save, log, system)
        else:
            raise NodeStateError('Cannot add tags to withdrawn registrations.')

    def add_tags(self, tags, auth=None, save=True, log=True, system=False):
        if self.retraction is None:
            super(Registration, self).add_tags(tags, auth, save, log, system)
        else:
            raise NodeStateError('Cannot add tags to withdrawn registrations.')

    def remove_tag(self, tag, auth, save=True):
        if self.retraction is None:
            super(Registration, self).remove_tag(tag, auth, save)
        else:
            raise NodeStateError('Cannot remove tags of withdrawn registrations.')

    def remove_tags(self, tags, auth, save=True):
        if self.retraction is None:
            super(Registration, self).remove_tags(tags, auth, save)
        else:
            raise NodeStateError('Cannot remove tags of withdrawn registrations.')

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            ('view_registration', 'Can view registration details'),
        )

class DraftRegistrationLog(ObjectIDMixin, BaseModel):
    """ Simple log to show status changes for DraftRegistrations
    Also, editable fields on registrations are logged.
    field - _id - primary key
    field - date - date of the action took place
    field - action - simple action to track what happened
    field - user - user who did the action
    """
    date = NonNaiveDateTimeField(default=timezone.now)
    action = models.CharField(max_length=255)
    draft = models.ForeignKey('DraftRegistration', related_name='logs',
                              null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey('OSFUser', db_index=True, null=True, blank=True, on_delete=models.CASCADE)
    params = DateTimeAwareJSONField(default=dict)

    SUBMITTED = 'submitted'
    REGISTERED = 'registered'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    EDITED_TITLE = 'edit_title'
    EDITED_DESCRIPTION = 'edit_description'
    CATEGORY_UPDATED = 'category_updated'

    CONTRIB_ADDED = 'contributor_added'
    CONTRIB_REMOVED = 'contributor_removed'
    CONTRIB_REORDERED = 'contributors_reordered'
    PERMISSIONS_UPDATED = 'permissions_updated'

    MADE_CONTRIBUTOR_VISIBLE = 'made_contributor_visible'
    MADE_CONTRIBUTOR_INVISIBLE = 'made_contributor_invisible'

    AFFILIATED_INSTITUTION_ADDED = 'affiliated_institution_added'
    AFFILIATED_INSTITUTION_REMOVED = 'affiliated_institution_removed'

    CHANGED_LICENSE = 'license_changed'

    TAG_ADDED = 'tag_added'
    TAG_REMOVED = 'tag_removed'

    def __repr__(self):
        return ('<DraftRegistrationLog({self.action!r}, date={self.date!r}), '
                'user={self.user!r} '
                'with id {self._id!r}>').format(self=self)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'


def get_default_id():
    from django.apps import apps
    RegistrationProvider = apps.get_model('osf', 'RegistrationProvider')
    return RegistrationProvider.get_default().id


class DraftRegistration(ObjectIDMixin, RegistrationResponseMixin, DirtyFieldsMixin,
        BaseModel, Loggable, EditableFieldsMixin, GuardianMixin):

    # Fields that are writable by DraftRegistration.update
    WRITABLE_WHITELIST = [
        'title',
        'description',
        'category',
        'node_license',
    ]

    URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/drafts/{draft_id}'

    # Overrides EditableFieldsMixin to make title not required
    title = models.TextField(validators=[validate_title], blank=True, default='')

    _contributors = models.ManyToManyField(OSFUser,
                                           through=DraftRegistrationContributor,
                                           related_name='draft_registrations')
    affiliated_institutions = models.ManyToManyField('Institution', related_name='draft_registrations')
    node_license = models.ForeignKey('NodeLicenseRecord', related_name='draft_registrations',
                                     on_delete=models.SET_NULL, null=True, blank=True)

    datetime_initiated = NonNaiveDateTimeField(auto_now_add=True)
    datetime_updated = NonNaiveDateTimeField(auto_now=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)

    # Original Node a draft registration is associated with
    branched_from = models.ForeignKey('AbstractNode', related_name='registered_draft',
                                      null=True, on_delete=models.CASCADE)

    initiator = models.ForeignKey('OSFUser', null=True, on_delete=models.CASCADE)
    provider = models.ForeignKey(
        'RegistrationProvider',
        related_name='draft_registrations',
        null=False,
        on_delete=models.CASCADE,
        default=get_default_id,
    )

    # Dictionary field mapping question id to a question's comments and answer
    # {
    #   <qid>: {
    #     'comments': [{
    #       'user': {
    #         'id': <uid>,
    #         'name': <name>
    #       },
    #       value: <value>,
    #       lastModified: <datetime>
    #     }],
    #     'value': <value>
    #   }
    # }
    registration_metadata = DateTimeAwareJSONField(default=dict, blank=True)
    registration_schema = models.ForeignKey('RegistrationSchema', null=True, on_delete=models.CASCADE)
    registered_node = models.ForeignKey('Registration', null=True, blank=True,
                                        related_name='draft_registration', on_delete=models.CASCADE)

    approval = models.ForeignKey('DraftRegistrationApproval', null=True, blank=True, on_delete=models.CASCADE)

    # Dictionary field mapping extra fields defined in the RegistrationSchema.schema to their
    # values. Defaults should be provided in the schema (e.g. 'paymentSent': false),
    # and these values are added to the DraftRegistration
    # TODO: Use "FIELD_ALIASES"?
    _metaschema_flags = DateTimeAwareJSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    # For ContributorMixin
    guardian_object_type = 'draft_registration'

    READ_DRAFT_REGISTRATION = 'read_{}'.format(guardian_object_type)
    WRITE_DRAFT_REGISTRATION = 'write_{}'.format(guardian_object_type)
    ADMIN_DRAFT_REGISTRATION = 'admin_{}'.format(guardian_object_type)

    # For ContributorMixin
    base_perms = [READ_DRAFT_REGISTRATION, WRITE_DRAFT_REGISTRATION, ADMIN_DRAFT_REGISTRATION]

    groups = {
        'read': (READ_DRAFT_REGISTRATION,),
        'write': (READ_DRAFT_REGISTRATION, WRITE_DRAFT_REGISTRATION,),
        'admin': (READ_DRAFT_REGISTRATION, WRITE_DRAFT_REGISTRATION, ADMIN_DRAFT_REGISTRATION,)
    }
    group_format = 'draft_registration_{self.id}_{group}'

    class Meta:
        permissions = (
            ('read_draft_registration', 'Can read the draft registration'),
            ('write_draft_registration', 'Can edit the draft registration'),
            ('admin_draft_registration', 'Can manage the draft registration'),
        )

    def __repr__(self):
        return ('<DraftRegistration(branched_from={self.branched_from!r}) '
                'with id {self._id!r}>').format(self=self)

    def get_registration_metadata(self, schema):
        # Overrides RegistrationResponseMixin
        return self.registration_metadata

    @property
    def file_storage_resource(self):
        # Overrides RegistrationResponseMixin
        return self.branched_from

    # lazily set flags
    @property
    def flags(self):
        if not self._metaschema_flags:
            self._metaschema_flags = {}
        meta_schema = self.registration_schema
        if meta_schema:
            schema = meta_schema.schema
            flags = schema.get('flags', {})
            dirty = False
            for flag, value in flags.items():
                if flag not in self._metaschema_flags:
                    self._metaschema_flags[flag] = value
                    dirty = True
            if dirty:
                self.save()
        return self._metaschema_flags

    @flags.setter
    def flags(self, flags):
        self._metaschema_flags.update(flags)

    @property
    def branched_from_type(self):
        if isinstance(self.branched_from, (DraftNode, Node)):
            return self.branched_from.__class__.__name__
        else:
            raise DraftRegistrationStateError

    @property
    def url(self):
        return self.URL_TEMPLATE.format(
            node_id=self.branched_from._id,
            draft_id=self._id
        )

    @property
    def _primary_key(self):
        return self._id

    @property
    def absolute_url(self):
        return urljoin(settings.DOMAIN, self.url)

    @property
    def absolute_api_v2_url(self):
        # Old draft registration URL - user new endpoints, through draft registration
        node = self.branched_from
        branched_type = self.branched_from_type
        if branched_type == 'DraftNode':
            path = '/draft_registrations/{}/'.format(self._id)
        elif branched_type == 'Node':
            path = '/nodes/{}/draft_registrations/{}/'.format(node._id, self._id)
        return api_v2_url(path)

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def requires_approval(self):
        return self.registration_schema.requires_approval

    @property
    def is_pending_review(self):
        return self.approval.is_pending_approval if (self.requires_approval and self.approval) else False

    @property
    def is_approved(self):
        if self.requires_approval:
            if not self.approval:
                return bool(self.registered_node)
            else:
                return self.approval.is_approved
        else:
            return False

    @property
    def is_rejected(self):
        if self.requires_approval:
            if not self.approval:
                return False
            else:
                return self.approval.is_rejected
        else:
            return False

    @property
    def status_logs(self):
        """ List of logs associated with this node"""
        return self.logs.all().order_by('date')

    @property
    def log_class(self):
        # Override for EditableFieldsMixin
        return DraftRegistrationLog

    @property
    def state_error(self):
        # Override for ContributorMixin
        return DraftRegistrationStateError

    @property
    def contributor_class(self):
        # Override for ContributorMixin
        return DraftRegistrationContributor

    def get_contributor_order(self):
        # Method needed for ContributorMixin
        return self.get_draftregistrationcontributor_order()

    def set_contributor_order(self, contributor_ids):
        # Method needed for ContributorMixin
        return self.set_draftregistrationcontributor_order(contributor_ids)

    @property
    def contributor_kwargs(self):
        # Override for ContributorMixin
        return {'draft_registration': self}

    @property
    def contributor_set(self):
        # Override for ContributorMixin
        return self.draftregistrationcontributor_set

    @property
    def order_by_contributor_field(self):
        # Property needed for ContributorMixin
        return 'draftregistrationcontributor___order'

    @property
    def admin_contributor_or_group_member_ids(self):
        # Overrides ContributorMixin
        # Draft Registrations don't have parents or group members at the moment, so this is just admin group member ids
        # Called when removing project subscriptions
        return self.get_group(ADMIN).user_set.filter(is_active=True).values_list('guids___id', flat=True)

    @property
    def creator(self):
        # Convenience property for testing contributor methods, which are
        # shared with other items that have creators
        return self.initiator

    @property
    def is_public(self):
        # Convenience property for sharing code with nodes
        return False

    @property
    def log_params(self):
        # Override for EditableFieldsMixin
        return {
            'draft_registration': self._id,
        }

    @property
    def visible_contributors(self):
        # Override for ContributorMixin
        return OSFUser.objects.filter(
            draftregistrationcontributor__draft_registration=self,
            draftregistrationcontributor__visible=True
        ).order_by(self.order_by_contributor_field)

    @property
    def contributor_email_template(self):
        # Override for ContributorMixin
        return 'draft_registration'

    @property
    def institutions_url(self):
        # For NodeInstitutionsRelationshipSerializer
        path = '/draft_registrations/{}/institutions/'.format(self._id)
        return api_v2_url(path)

    @property
    def institutions_relationship_url(self):
        # For NodeInstitutionsRelationshipSerializer
        path = '/draft_registrations/{}/relationships/institutions/'.format(self._id)
        return api_v2_url(path)

    def update_search(self):
        # Override for AffiliatedInstitutionMixin, not sending DraftRegs to search
        pass

    def can_view(self, auth):
        """Does the user have permission to view the draft registration?
        Checking permissions directly on the draft, not the node.
        """
        if not auth:
            return False
        return auth.user and self.has_permission(auth.user, READ)

    def can_edit(self, auth=None, user=None):
        """Return if a user is authorized to edit this draft_registration.
        Must specify one of (`auth`, `user`).

        :param Auth auth: Auth object to check
        :param User user: User object to check
        :returns: Whether user has permission to edit this draft_registration.
        """
        if not auth and not user:
            raise ValueError('Must pass either `auth` or `user`')
        if auth and user:
            raise ValueError('Cannot pass both `auth` and `user`')
        user = user or auth.user
        return (user and self.has_permission(user, WRITE))

    def get_addons(self):
        # Override for ContributorMixin, Draft Registrations don't have addons
        return []

    # Override Taggable
    def add_tag_log(self, tag, auth):
        self.add_log(
            action=DraftRegistrationLog.TAG_ADDED,
            params={
                'draft_registration': self._id,
                'tag': tag.name
            },
            auth=auth,
            save=False
        )

    @property
    def license(self):
        if self.node_license_id:
            return self.node_license
        return None

    @property
    def all_tags(self):
        """Return a queryset containing all of this draft's tags (incl. system tags)."""
        # Tag's default manager only returns non-system tags, so we can't use self.tags
        return Tag.all_tags.filter(draftregistration_tagged=self)

    @property
    def system_tags(self):
        """The system tags associated with this draft registration. This currently returns a list of string
        names for the tags, for compatibility with v1. Eventually, we can just return the
        QuerySet.
        """
        return self.all_tags.filter(system=True).values_list('name', flat=True)

    @classmethod
    def create_from_node(cls, user, schema, node=None, data=None, provider=None):
        if not provider:
            provider = RegistrationProvider.get_default()

        if provider.is_default:
            # If the default provider doesn't have schemas specified yet, allow all schemas
            if provider.schemas.exists():
                provider.validate_schema(schema)
        else:
            provider.validate_schema(schema)

        if not node:
            # If no node provided, a DraftNode is created for you
            node = DraftNode.objects.create(creator=user, title='Untitled')

        if not (isinstance(node, Node) or isinstance(node, DraftNode)):
            raise DraftRegistrationStateError()

        draft = cls(
            initiator=user,
            branched_from=node,
            registration_schema=schema,
            registration_metadata=data or {},
            provider=provider,
        )
        draft.save()
        draft.copy_editable_fields(node, Auth(user), save=True, contributors=False)
        draft.update(data)
        return draft

    def get_root(self):
        return self

    def copy_contributors_from(self, resource):
        """
        Copies the contibutors from the resource (including permissions and visibility)
        into this draft registration.
        Visibility, order, draft, and user are stored in DraftRegistrationContributor table.
        Permissions are stored in guardian tables (use add_permission)
        """

        contribs = []
        current_contributors = self.contributor_set.values_list('user_id', flat=True)
        for contrib in resource.contributor_set.all():
            if contrib.user.id not in current_contributors:
                permission = contrib.permission
                new_contrib = DraftRegistrationContributor(
                    draft_registration=self,
                    _order=contrib._order,
                    visible=contrib.visible,
                    user=contrib.user
                )
                contribs.append(new_contrib)
                self.add_permission(contrib.user, permission, save=True)
        DraftRegistrationContributor.objects.bulk_create(contribs)

    def update_metadata(self, metadata):
        changes = []
        # Prevent comments on approved drafts
        if not self.is_approved:
            for question_id, value in metadata.items():
                old_value = self.registration_metadata.get(question_id)
                if old_value:
                    old_comments = {
                        comment['created']: comment
                        for comment in old_value.get('comments', [])
                    }
                    new_comments = {
                        comment['created']: comment
                        for comment in value.get('comments', [])
                    }
                    old_comments.update(new_comments)
                    metadata[question_id]['comments'] = sorted(
                        old_comments.values(),
                        key=lambda c: c['created']
                    )
                    if old_value.get('value') != value.get('value'):
                        changes.append(question_id)
                else:
                    changes.append(question_id)
        self.registration_metadata.update(metadata)

        # Write to registration_responses also (new workflow)
        registration_responses = self.flatten_registration_metadata()
        self.registration_responses.update(registration_responses)
        return changes

    def update_registration_responses(self, registration_responses):
        """
        New workflow - update_registration_responses.  This should have been
        validated before this method is called.  If writing to registration_responses
        field, persist the expanded version of this to Draft.registration_metadata.
        """
        registration_responses = self.unescape_registration_file_names(registration_responses)
        self.registration_responses.update(registration_responses)
        registration_metadata = self.expand_registration_responses()
        self.registration_metadata = registration_metadata
        return

    def unescape_registration_file_names(self, registration_responses):
        if registration_responses.get('uploader', []):
            for upload in registration_responses.get('uploader', []):
                upload['file_name'] = html.unescape(upload['file_name'])
        return registration_responses

    def submit_for_review(self, initiated_by, meta, save=False):
        approval = DraftRegistrationApproval(
            meta=meta
        )
        approval.save()
        self.approval = approval
        self.add_status_log(initiated_by, DraftRegistrationLog.SUBMITTED)
        if save:
            self.save()

    def register(self, auth, save=False, child_ids=None):
        node = self.branched_from

        if not self.title:
            raise NodeStateError('Draft Registration must have title to be registered')

        # Create the registration
        registration = node.register_node(
            schema=self.registration_schema,
            auth=auth,
            draft_registration=self,
            child_ids=child_ids,
            provider=self.provider
        )
        self.registered_node = registration
        self.add_status_log(auth.user, DraftRegistrationLog.REGISTERED)

        self.copy_contributors_from(node)

        if save:
            self.save()
            registration.save()

        return registration

    def approve(self, user):
        self.approval.approve(user)
        self.refresh_from_db()
        self.add_status_log(user, DraftRegistrationLog.APPROVED)
        self.approval.save()

    def reject(self, user):
        self.approval.reject(user)
        self.add_status_log(user, DraftRegistrationLog.REJECTED)
        self.approval.save()

    def add_status_log(self, user, action):
        params = {
            'draft_registration': self._id,
        },
        log = DraftRegistrationLog(action=action, user=user, draft=self, params=params)
        log.save()

    def validate_metadata(self, *args, **kwargs):
        """
        Validates draft's metadata
        """
        return self.registration_schema.validate_metadata(*args, **kwargs)

    def validate_registration_responses(self, *args, **kwargs):
        """
        Validates draft's registration_responses
        """
        return self.registration_schema.validate_registration_responses(*args, **kwargs)

    def add_log(self, action, params, auth, save=True):
        """
        Tentative - probably need to combine with add_status_log
        """
        user = auth.user if auth else None

        params['draft_registration'] = params.get('draft_registration') or self._id

        log = DraftRegistrationLog(
            action=action, user=user,
            params=params, draft=self
        )
        log.save()
        return log

    # Overrides ContributorMixin
    def _add_related_source_tags(self, contributor):
        # The related source tag behavior for draft registration is currently undefined
        # Therefore we don't add any source tags to it
        pass

    def save(self, *args, **kwargs):
        if 'old_subjects' in kwargs.keys():
            kwargs.pop('old_subjects')
        return super(DraftRegistration, self).save(*args, **kwargs)

    def update(self, fields, auth=None, save=True):
        """Update the draft registration with the given fields.
        :param dict fields: Dictionary of field_name:value pairs.
        :param Auth auth: Auth object for the user making the update.
        :param bool save: Whether to save after updating the object.
        """
        if not fields:  # Bail out early if there are no fields to update
            return False
        for key, value in fields.items():
            if key not in self.WRITABLE_WHITELIST:
                continue
            if key == 'title':
                self.set_title(title=value, auth=auth, save=False, allow_blank=True)
            elif key == 'description':
                self.set_description(description=value, auth=auth, save=False)
            elif key == 'category':
                self.set_category(category=value, auth=auth, save=False)
            elif key == 'node_license':
                self.set_node_license(
                    {
                        'id': value.get('id'),
                        'year': value.get('year'),
                        'copyrightHolders': value.get('copyrightHolders') or value.get('copyright_holders', [])
                    },
                    auth,
                    save=save
                )
        if save:
            updated = self.get_dirty_fields()
            self.save()

        return updated


class DraftRegistrationUserObjectPermission(UserObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - User models - we typically add object
    perms directly to Django groups instead of users, so this will be used infrequently
    """
    content_object = models.ForeignKey(DraftRegistration, on_delete=models.CASCADE)


class DraftRegistrationGroupObjectPermission(GroupObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - Group models. Makes permission checks faster.
    This table gives a Django group a particular permission to a DraftRegistration.
    For example, every time a draft reg is created, an admin, write, and read Django group
    are created for the draft reg. The "write" group has write/read perms to the draft reg.
    Those links are stored here:  content_object_id (draft_registration_id), group_id, permission_id
    """
    content_object = models.ForeignKey(DraftRegistration, on_delete=models.CASCADE)


@receiver(post_save, sender='osf.DraftRegistration')
def create_django_groups_for_draft_registration(sender, instance, created, **kwargs):
    if created:
        instance.update_group_permissions()

        initiator = instance.initiator

        if instance.branched_from.contributor_set.filter(user=initiator).exists():
            initiator_node_contributor = instance.branched_from.contributor_set.get(user=initiator)
            initiator_visibility = initiator_node_contributor.visible
            initiator_order = initiator_node_contributor._order

            DraftRegistrationContributor.objects.get_or_create(
                user=initiator,
                draft_registration=instance,
                visible=initiator_visibility,
                _order=initiator_order
            )
        else:
            DraftRegistrationContributor.objects.get_or_create(
                user=initiator,
                draft_registration=instance,
                visible=True,
            )
        instance.add_permission(initiator, ADMIN)
