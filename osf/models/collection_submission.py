from past.builtins import basestring
import logging

from django.db import models
from django.utils.functional import cached_property
from framework.exceptions import PermissionsError

from osf.models.base import BaseModel
from osf.models.mixins import TaxonomizableMixin
from osf.utils.notifications import notify_submit
from osf.utils.permissions import ADMIN, READ
from website.util import api_v2_url
from website.search.exceptions import SearchUnavailableError
from osf.utils.workflows import CollectionSubmissionsTriggers, CollectionSubmissionStates
from website import mails, settings
from osf.utils.machines import CollectionSubmissionMachine
from django.db.models.signals import post_save
from django.dispatch import receiver


logger = logging.getLogger(__name__)


class CollectionSubmission(TaxonomizableMixin, BaseModel):
    primary_identifier_name = 'guid___id'

    class Meta:
        order_with_respect_to = 'collection'
        unique_together = ('collection', 'guid')

    collection = models.ForeignKey('Collection', on_delete=models.CASCADE)
    guid = models.ForeignKey('Guid', on_delete=models.CASCADE)
    creator = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    collected_type = models.CharField(blank=True, max_length=127)
    status = models.CharField(blank=True, max_length=127)
    volume = models.CharField(blank=True, max_length=127)
    issue = models.CharField(blank=True, max_length=127)
    program_area = models.CharField(blank=True, max_length=127)
    school_type = models.CharField(blank=True, max_length=127)
    study_design = models.CharField(blank=True, max_length=127)
    machine_state = models.IntegerField(
        choices=CollectionSubmissionStates.int_field_choices(),
        default=CollectionSubmissionStates.IN_PROGRESS,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = CollectionSubmissionMachine(
            model=self,
            active_state=self.state,
            state_property_name='state'
        )

    @property
    def state(self):
        return CollectionSubmissionStates(self.machine_state)

    @property
    def is_moderated(self):
        return bool(self.collection.provider) and self.collection.provider.reviews_workflow == 'pre-moderation'

    @state.setter
    def state(self, new_state):
        self.machine_state = new_state.value

    def _notify_moderated_pending(self, event_data):
        user = event_data.kwargs['user']

        notify_submit(self.guid.referent, user)  # notifies moderators

        for contributor in self.guid.referent.contributors:
            mails.send_mail(
                to_addr=contributor.username,
                mail=mails.COLLECTION_SUBMISSION_SUBMITTED(self.creator, self.guid.referent),
                user=contributor,
                submitter=self.creator,
                is_initator=self.creator == contributor,
                is_admin=self.guid.referent.has_permission(contributor, ADMIN),
                is_registered_contrib=contributor.is_registered,
                collection=self.collection,
                claim_url=contributor.unclaimed_records.get(self.guid.referent._id, None),
                node=self.guid.referent,
                domain=settings.DOMAIN,
                osf_contact_email=settings.OSF_CONTACT_EMAIL,
            )

    def _validate_accept(self, event_data):
        user = event_data.kwargs['user']
        if user is None:
            raise PermissionsError(f'{user} must have moderator permissions.')

        is_moderator = user.has_perm('accept_submissions', self.collection.provider)
        if not is_moderator:
            raise PermissionsError(f'{user} must have moderator permissions.')

    def _notify_moderated_accepted(self, event_data):
        for contributor in self.guid.referent.contributors:
            mails.send_mail(
                to_addr=contributor.username,
                mail=mails.COLLECTION_SUBMISSION_ACCEPTED(self.collection, self.guid.referent),
                user=contributor,
                submitter=event_data.kwargs['user'],
                is_admin=self.guid.referent.has_permission(contributor, ADMIN),
                collection=self.collection,
                node=self.guid.referent,
                domain=settings.DOMAIN,
                osf_contact_email=settings.OSF_CONTACT_EMAIL,
            )

    def _validate_reject(self, event_data):
        user = event_data.kwargs['user']
        if user is None:
            raise PermissionsError(f'{user} must have moderator permissions.')

        is_moderator = user.has_perm('reject_submissions', self.collection.provider)
        if not is_moderator:
            raise PermissionsError(f'{user} must have moderator permissions.')

    def _notify_moderated_rejected(self, event_data):
        for contributor in self.guid.referent.contributors:
            mails.send_mail(
                to_addr=contributor.username,
                mail=mails.COLLECTION_SUBMISSION_REJECTED(self.collection, self.guid.referent),
                user=contributor,
                is_admin=self.guid.referent.has_permission(contributor, ADMIN),
                collection=self.collection,
                node=self.guid.referent,
                rejection_justification=event_data.kwargs['comment'],
                osf_contact_email=settings.OSF_CONTACT_EMAIL,
            )

    def _validate_remove(self, event_data):
        user = event_data.kwargs['user']
        force = event_data.kwargs.get('force')
        if force:
            return

        if user is None:
            raise PermissionsError(f'{user} must have moderator or admin permissions.')

        is_admin = self.guid.referent.has_permission(user, ADMIN)
        is_moderator = user.has_perm('withdraw_submissions', self.collection.provider)
        if self.is_moderated:
            if not is_moderator and not is_admin:
                raise PermissionsError(f'{user} must have moderator or admin permissions.')
        else:
            if not is_admin:
                raise PermissionsError(f'{user} must have moderator or admin permissions.')

    def _notify_removed(self, event_data):
        force = event_data.kwargs.get('force')
        if force:
            return

        user = event_data.kwargs['user']
        removed_due_to_privacy = event_data.kwargs.get('removed_due_to_privacy')
        is_moderator = user.has_perm('withdraw_submissions', self.collection.provider)
        is_admin = self.guid.referent.has_permission(user, ADMIN)
        if removed_due_to_privacy:
            if self.is_moderated:
                for moderator in self.collection.moderators:
                    mails.send_mail(
                        to_addr=moderator.username,
                        mail=mails.COLLECTION_SUBMISSION_REMOVED_PRIVATE(self.collection, self.guid.referent),
                        user=moderator,
                        remover=user,
                        is_admin=self.guid.referent.has_permission(moderator, ADMIN),
                        collection=self.collection,
                        node=self.guid.referent,
                        domain=settings.DOMAIN,
                        osf_contact_email=settings.OSF_CONTACT_EMAIL,
                    )
            for contributor in self.guid.referent.contributors.all():
                mails.send_mail(
                    to_addr=contributor.username,
                    mail=mails.COLLECTION_SUBMISSION_REMOVED_PRIVATE(self.collection, self.guid.referent),
                    user=contributor,
                    remover=user,
                    is_admin=self.guid.referent.has_permission(contributor, ADMIN),
                    collection=self.collection,
                    node=self.guid.referent,
                    domain=settings.DOMAIN,
                    osf_contact_email=settings.OSF_CONTACT_EMAIL,
                )
        elif is_moderator:
            for contributor in self.guid.referent.contributors:
                mails.send_mail(
                    to_addr=contributor.username,
                    mail=mails.COLLECTION_SUBMISSION_REMOVED_MODERATOR(self.collection, self.guid.referent),
                    user=contributor,
                    remover=event_data.kwargs['user'],
                    is_admin=self.guid.referent.has_permission(contributor, ADMIN),
                    collection=self.collection,
                    node=self.guid.referent,
                    osf_contact_email=settings.OSF_CONTACT_EMAIL,
                )
        elif is_admin:
            if self.is_moderated:
                for moderator in self.collection.moderators:
                    mails.send_mail(
                        to_addr=moderator.username,
                        mail=mails.COLLECTION_SUBMISSION_REMOVED_ADMIN(self.collection, self.guid.referent),
                        user=moderator,
                        remover=event_data.kwargs['user'],
                        is_admin=self.guid.referent.has_permission(moderator, ADMIN),
                        collection=self.collection,
                        node=self.guid.referent,
                        osf_contact_email=settings.OSF_CONTACT_EMAIL,
                    )
            for contributor in self.guid.referent.contributors:
                mails.send_mail(
                    to_addr=contributor.username,
                    mail=mails.COLLECTION_SUBMISSION_REMOVED_ADMIN(self.collection, self.guid.referent),
                    user=contributor,
                    remover=event_data.kwargs['user'],
                    is_admin=self.guid.referent.has_permission(contributor, ADMIN),
                    collection=self.collection,
                    node=self.guid.referent,
                    osf_contact_email=settings.OSF_CONTACT_EMAIL,
                )
        else:
            raise NotImplementedError()

    def _validate_resubmit(self, event_data):
        user = event_data.kwargs['user']
        if user is None:
            raise PermissionsError(f'{user} must have admin permissions.')

        is_admin = self.guid.referent.has_permission(user, ADMIN)
        if not is_admin:
            raise PermissionsError(f'{user} must have admin permissions.')

    def _validate_unmoderated_resubmit(self, event_data):
        user = event_data.kwargs['user']
        if user is None:
            raise PermissionsError(f'{user} must have contributor permissions.')

        is_contributor = self.guid.referent.has_permission(user, READ)
        if not is_contributor:
            raise PermissionsError(f'{user} must have contributor permissions.')

    def _remove_from_search(self, event_data):
        self.remove_from_index()

    def _save_transition(self, event_data):
        '''Save changes here and write the action.'''
        self.save()
        from_state = CollectionSubmissionStates[event_data.transition.source]
        to_state = self.state

        trigger = CollectionSubmissionsTriggers.from_db_name(event_data.event.name)
        if trigger is None:
            return

        self.actions.create(
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            creator=event_data.kwargs.get('user', self.creator),
            comment=event_data.kwargs.get('comment', '')
        )

    @cached_property
    def _id(self):
        return '{}-{}'.format(self.guid._id, self.collection._id)

    @classmethod
    def load(cls, data, select_for_update=False):
        try:
            collection_submission_id, collection_id = data.split('-')
        except ValueError:
            raise ValueError('Invalid CollectionSubmission object <_id {}>'.format(data))
        else:
            if collection_submission_id and collection_id:
                try:
                    if isinstance(data, basestring):
                        return (cls.objects.get(guid___id=collection_submission_id, collection__guids___id=collection_id) if not select_for_update
                                else cls.objects.filter(guid___id=collection_submission_id, collection__guids___id=collection_id).select_for_update().get())
                except cls.DoesNotExist:
                    return None
            return None

    @property
    def absolute_api_v2_url(self):
        path = '/collections/{}/collection_submissions/{}/'.format(self.collection._id, self.guid._id)
        return api_v2_url(path)

    def update_index(self):
        if self.collection.is_public:
            from website.search.search import update_collected_metadata
            try:
                update_collected_metadata(self.guid._id, collection_id=self.collection.id)
            except SearchUnavailableError as e:
                logger.exception(e)

    def remove_from_index(self):
        from website.search.search import update_collected_metadata
        try:
            update_collected_metadata(self.guid._id, collection_id=self.collection.id, op='delete')
        except SearchUnavailableError as e:
            logger.exception(e)

    def save(self, *args, **kwargs):
        kwargs.pop('old_subjects', None)  # Not indexing this, trash it
        ret = super(CollectionSubmission, self).save(*args, **kwargs)
        self.update_index()
        return ret


@receiver(post_save, sender=CollectionSubmission)
def create_submission_action(sender, instance, created, **kwargs):
    if created:
        instance.submit(user=instance.creator, comment='Initial submission action')
