import logging
import datetime
from future.moves.urllib.parse import urljoin

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from framework.auth import Auth
from framework.exceptions import PermissionsError
from osf.utils.fields import NonNaiveDateTimeField
from osf.exceptions import NodeStateError
from website.util import api_v2_url
from website import settings
from website.archiver import ARCHIVER_INITIATED

from osf.models import (
    OSFUser, RegistrationSchema,
    Retraction, Embargo, DraftRegistrationApproval,
    EmbargoTerminationApproval,
)

from osf.models.archive import ArchiveJob
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.node import AbstractNode
from osf.models.nodelog import NodeLog
from osf.models.provider import RegistrationProvider
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

logger = logging.getLogger(__name__)


class Registration(AbstractNode):

    WRITABLE_WHITELIST = [
        'article_doi',
        'description',
        'is_public',
        'node_license',
        'category',
    ]
    provider = models.ForeignKey('RegistrationProvider', related_name='registrations', null=True)
    registered_date = NonNaiveDateTimeField(db_index=True, null=True, blank=True)
    registered_user = models.ForeignKey(OSFUser,
                                        related_name='related_to',
                                        on_delete=models.SET_NULL,
                                        null=True, blank=True)

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

    @staticmethod
    def find_failed_registrations():
        expired_if_before = timezone.now() - settings.ARCHIVE_TIMEOUT_TIMEDELTA
        node_id_list = ArchiveJob.objects.filter(sent=False, datetime_initiated__lt=expired_if_before, status=ARCHIVER_INITIATED).values_list('dst_node', flat=True)
        root_nodes_id = AbstractNode.objects.filter(id__in=node_id_list).values_list('root', flat=True).distinct()
        stuck_regs = AbstractNode.objects.filter(id__in=root_nodes_id, is_deleted=False)
        return stuck_regs

    @property
    def registered_schema_id(self):
        if self.registered_schema.exists():
            return self.registered_schema.first()._id
        return None

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
            root.embargo_termination_approval or
            root.retraction or
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
        if not self.is_admin_contributor(user):
            raise PermissionsError('Only admins may embargo a registration')
        if not self._is_embargo_date_valid(end_date):
            if (end_date - timezone.now()) >= settings.EMBARGO_END_DATE_MIN:
                raise ValidationError('Registrations can only be embargoed for up to four years.')
            raise ValidationError('Embargo end date must be at least three days in the future.')

        embargo = self._initiate_embargo(user, end_date,
                                         for_existing_registration=for_existing_registration,
                                         notify_initiator_on_complete=notify_initiator_on_complete)

        self.registered_from.add_log(
            action=NodeLog.EMBARGO_INITIATED,
            params={
                'node': self.registered_from._id,
                'registration': self._id,
                'embargo_id': embargo._id,
            },
            auth=Auth(user),
            save=True,
        )
        if self.is_public:
            self.set_privacy('private', Auth(user))

    def request_embargo_termination(self, auth):
        """Initiates an EmbargoTerminationApproval to lift this Embargoed Registration's
        embargo early."""
        if not self.is_embargoed:
            raise NodeStateError('This node is not under active embargo')
        if not self.root == self:
            raise NodeStateError('Only the root of an embargoed registration can request termination')

        approval = EmbargoTerminationApproval(
            initiated_by=auth.user,
            embargoed_registration=self,
        )
        admins = [admin for admin in self.root.get_admin_contributors_recursive(unique_users=True)]
        for (admin, node) in admins:
            approval.add_authorizer(admin, node=node)
        approval.save()
        approval.ask(admins)
        self.embargo_termination_approval = approval
        self.save()
        return approval

    def terminate_embargo(self, auth):
        """Handles the actual early termination of an Embargoed registration.
        Adds a log to the registered_from Node.
        """
        if not self.is_embargoed:
            raise NodeStateError('This node is not under active embargo')

        self.registered_from.add_log(
            action=NodeLog.EMBARGO_TERMINATED,
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

    def _initiate_retraction(self, user, justification=None):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param justification: Justification, if given, for retraction
        """
        self.retraction = Retraction.objects.create(
            initiated_by=user,
            justification=justification or None,  # make empty strings None
            state=Retraction.UNAPPROVED
        )
        self.save()
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            self.retraction.add_authorizer(admin, node)
        self.retraction.save()  # Save retraction approval state
        return self.retraction

    def retract_registration(self, user, justification=None, save=True):
        """Retract public registration. Instantiate new Retraction object
        and associate it with the respective registration.
        """

        if not self.is_public and not (self.embargo_end_date or self.is_pending_embargo):
            raise NodeStateError('Only public or embargoed registrations may be withdrawn.')

        if self.root_id != self.id:
            raise NodeStateError('Withdrawal of non-parent registrations is not permitted.')

        retraction = self._initiate_retraction(user, justification)
        self.registered_from.add_log(
            action=NodeLog.RETRACTION_INITIATED,
            params={
                'node': self.registered_from._id,
                'registration': self._id,
                'retraction_id': retraction._id,
            },
            auth=Auth(user),
        )
        self.retraction = retraction
        if save:
            self.save()
        return retraction

    def copy_unclaimed_records(self):
        """Copies unclaimed_records to unregistered contributors from the registered_from node"""
        registered_from_id = self.registered_from._id
        for contributor in self.contributors.filter(is_registered=False):
            record = contributor.unclaimed_records.get(registered_from_id)
            if record:
                contributor.unclaimed_records[self._id] = record
                contributor.save()

    def delete_registration_tree(self, save=False):
        logger.debug('Marking registration {} as deleted'.format(self._id))
        self.is_deleted = True
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

    field - _id - primary key
    field - date - date of the action took place
    field - action - simple action to track what happened
    field - user - user who did the action
    """
    date = NonNaiveDateTimeField(default=timezone.now)
    action = models.CharField(max_length=255)
    draft = models.ForeignKey('DraftRegistration', related_name='logs',
                              null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey('OSFUser', null=True, on_delete=models.CASCADE)

    SUBMITTED = 'submitted'
    REGISTERED = 'registered'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    def __repr__(self):
        return ('<DraftRegistrationLog({self.action!r}, date={self.date!r}), '
                'user={self.user!r} '
                'with id {self._id!r}>').format(self=self)


class DraftRegistration(ObjectIDMixin, BaseModel):
    URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/drafts/{draft_id}'

    datetime_initiated = NonNaiveDateTimeField(auto_now_add=True)
    datetime_updated = NonNaiveDateTimeField(auto_now=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)

    # Original Node a draft registration is associated with
    branched_from = models.ForeignKey('Node', related_name='registered_draft',
                                      null=True, on_delete=models.CASCADE)

    initiator = models.ForeignKey('OSFUser', null=True, on_delete=models.CASCADE)
    provider = models.ForeignKey('RegistrationProvider', related_name='draft_registrations', null=True)

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

    def __repr__(self):
        return ('<DraftRegistration(branched_from={self.branched_from!r}) '
                'with id {self._id!r}>').format(self=self)

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
    def url(self):
        return self.URL_TEMPLATE.format(
            node_id=self.branched_from._id,
            draft_id=self._id
        )

    @property
    def absolute_url(self):
        return urljoin(settings.DOMAIN, self.url)

    @property
    def absolute_api_v2_url(self):
        node = self.branched_from
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

    @classmethod
    def create_from_node(cls, node, user, schema, data=None, provider=None):
        if not provider:
            provider = RegistrationProvider.load('osf')
        draft = cls(
            initiator=user,
            branched_from=node,
            registration_schema=schema,
            registration_metadata=data or {},
            provider=provider,
        )
        draft.save()
        return draft

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
        return changes

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

        # Create the registration
        register = node.register_node(
            schema=self.registration_schema,
            auth=auth,
            data=self.registration_metadata,
            child_ids=child_ids,
            provider=self.provider
        )
        self.registered_node = register
        self.add_status_log(auth.user, DraftRegistrationLog.REGISTERED)
        if save:
            self.save()
        return register

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
        log = DraftRegistrationLog(action=action, user=user, draft=self)
        log.save()

    def validate_metadata(self, *args, **kwargs):
        """
        Validates draft's metadata
        """
        return self.registration_schema.validate_metadata(*args, **kwargs)
