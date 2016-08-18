import urlparse

from django.utils import timezone
from django.db import models

from website.exceptions import NodeStateError
from website import settings

from osf_models.models import (
    OSFUser, MetaSchema, RegistrationApproval,
    Retraction, Embargo, DraftRegistrationApproval,
    EmbargoTerminationApproval,
)
from osf_models.models.base import BaseModel, ObjectIDMixin
from osf_models.models.node import AbstractNode
from osf_models.utils.base import api_v2_url
from osf_models.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class Registration(AbstractNode):
    is_registration = models.NullBooleanField(default=False, db_index=True)  # TODO SEPARATE CLASS
    registered_date = models.DateTimeField(db_index=True, null=True, blank=True)
    registered_user = models.ForeignKey(OSFUser,
                                        related_name='related_to',
                                        on_delete=models.SET_NULL,
                                        null=True, blank=True)

    registered_schema = models.ManyToManyField(MetaSchema)

    registered_meta = DateTimeAwareJSONField(default=dict, blank=True)
    # TODO Add back in once dependencies are resolved
    registration_approval = models.ForeignKey(RegistrationApproval, null=True, blank=True)
    retraction = models.ForeignKey(Retraction, null=True, blank=True)
    embargo = models.ForeignKey(Embargo, null=True, blank=True)

    registered_from = models.ForeignKey('self',
                                        related_name='registrations',
                                        on_delete=models.SET_NULL,
                                        null=True, blank=True)
    # Sanctions
    registration_approval = models.ForeignKey('RegistrationApproval',
                                            related_name='registrations',
                                            null=True, blank=True,
                                            on_delete=models.SET_NULL)
    retration = models.ForeignKey('Retraction',
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

    @property
    def archive_job(self):
        return self.archive_jobs.first() if self.archive_jobs.count() else None

    @property
    def sanction(self):
        sanction = (
            self.embargo_termination_approval or
            self.retraction or
            self.embargo or
            self.registration_approval
        )
        if sanction:
            return sanction
        elif self.parent_node:
            return self.parent_node.sanction
        else:
            return None

    @property
    def is_pending_embargo(self):
        if self.embargo is None:
            if self.parent_node:
                return self.parent_node.is_pending_embargo
            return False
        return self.embargo.is_pending_approval

    @property
    def is_pending_embargo_for_existing_registration(self):
        """ Returns True if Node has an Embargo pending approval for an
        existing registrations. This is used specifically to ensure
        registrations pre-dating the Embargo feature do not get deleted if
        their respective Embargo request is rejected.
        """
        if self.embargo is None:
            if self.parent_node:
                return self.parent_node.is_pending_embargo_for_existing_registration
            return False
        return self.embargo.pending_registration

    @property
    def is_pending_registration(self):
        if not self.is_registration:
            return False
        if self.registration_approval is None:
            if self.parent_node:
                return self.parent_node.is_pending_registration
            return False
        return self.registration_approval.is_pending_approval

    @property
    def is_embargoed(self):
        """A Node is embargoed if:
        - it has an associated Embargo record
        - that record has been approved
        - the node is not public (embargo not yet lifted)
        """
        if self.embargo is None:
            if self.parent_node:
                return self.parent_node.is_embargoed
        return self.embargo and self.embargo.is_approved and not self.is_public

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

class DraftRegistrationLog(ObjectIDMixin, BaseModel):
    """ Simple log to show status changes for DraftRegistrations

    field - _id - primary key
    field - date - date of the action took place
    field - action - simple action to track what happened
    field - user - user who did the action
    """
    date = models.DateTimeField()  # auto_add=True)
    action = models.CharField(max_length=255)
    draft = models.ForeignKey('DraftRegistration', related_name='logs', null=True)
    user = models.ForeignKey('OSFUser', null=True)

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

    datetime_initiated = models.DateTimeField(default=timezone.now)  # auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)
    # Original Node a draft registration is associated with
    branched_from = models.ForeignKey('Node', null=True, related_name='registered_draft')

    initiator = models.ForeignKey('OSFUser', null=True)

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
    registration_metadata = DateTimeAwareJSONField(default=dict)
    registration_schema = models.ForeignKey('MetaSchema', null=True)
    registered_node = models.ForeignKey('Node', null=True, blank=True, related_name='draft_registration')

    approval = models.ForeignKey('DraftRegistrationApproval', null=True, blank=True)

    # Dictionary field mapping extra fields defined in the MetaSchema.schema to their
    # values. Defaults should be provided in the schema (e.g. 'paymentSent': false),
    # and these values are added to the DraftRegistration
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
            for flag, value in flags.iteritems():
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
            node_id=self.branched_from,
            draft_id=self._id
        )

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)

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
                return False
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
        return self.logs.all().order('date')

    @classmethod
    def create_from_node(cls, node, user, schema, data=None):
        draft = cls(
            initiator=user,
            branched_from=node,
            registration_schema=schema,
            registration_metadata=data or {},
        )
        draft.save()
        return draft

    def update_metadata(self, metadata):
        changes = []
        # Prevent comments on approved drafts
        if not self.is_approved:
            for question_id, value in metadata.iteritems():
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
            initiated_by=initiated_by,
            meta=meta
        )
        approval.save()
        self.approval = approval
        self.add_status_log(initiated_by, DraftRegistrationLog.SUBMITTED)
        if save:
            self.save()

    def register(self, auth, save=False):
        node = self.branched_from

        # Create the registration
        register = node.register_node(
            schema=self.registration_schema,
            auth=auth,
            data=self.registration_metadata
        )
        self.registered_node = register
        self.add_status_log(auth.user, DraftRegistrationLog.REGISTERED)
        if save:
            self.save()
        return register

    def approve(self, user):
        self.approval.approve(user)
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
