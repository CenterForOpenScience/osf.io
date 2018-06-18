# -*- coding: utf-8 -*-
import urlparse
import logging

from dirtyfields import DirtyFieldsMixin
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError

from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from framework.exceptions import PermissionsError
from osf.models.mixins import ReviewableMixin
from osf.models import NodeLog, OSFUser
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.workflows import ReviewStates
from osf.utils.permissions import ADMIN
from osf.utils.requests import DummyRequest, get_request_and_user_id, get_headers_from_request
from website.notifications.emails import get_user_subscriptions
from website.notifications import utils
from website.preprints.tasks import on_preprint_updated
from website.project.licenses import set_license
from website.util import api_v2_url
from website.identifiers.clients import CrossRefClient, ECSArXivCrossRefClient
from website import settings, mails

from osf.models.base import BaseModel, GuidMixin
from osf.models.identifiers import IdentifierMixin, Identifier
from osf.models.mixins import TaxonomizableMixin
from osf.models.spam import SpamMixin

logger = logging.getLogger(__name__)

class PreprintService(DirtyFieldsMixin, SpamMixin, GuidMixin, IdentifierMixin, ReviewableMixin, TaxonomizableMixin, BaseModel):
    SPAM_CHECK_FIELDS = set()

    provider = models.ForeignKey('osf.PreprintProvider',
                                 on_delete=models.SET_NULL,
                                 related_name='preprint_services',
                                 null=True, blank=True, db_index=True)
    node = models.ForeignKey('osf.AbstractNode', on_delete=models.SET_NULL,
                             related_name='preprints',
                             null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    date_published = NonNaiveDateTimeField(null=True, blank=True)
    original_publication_date = NonNaiveDateTimeField(null=True, blank=True)
    license = models.ForeignKey('osf.NodeLicenseRecord',
                                on_delete=models.SET_NULL, null=True, blank=True)

    identifiers = GenericRelation(Identifier, related_query_name='preprintservices')
    preprint_doi_created = NonNaiveDateTimeField(default=None, null=True, blank=True)
    date_withdrawn = NonNaiveDateTimeField(default=None, null=True, blank=True)
    withdrawal_justification = models.TextField(default='', blank=True)
    ever_public = models.BooleanField(default=False, blank=True)

    class Meta:
        unique_together = ('node', 'provider')
        permissions = (
            ('view_preprintservice', 'Can view preprint service details in the admin app.'),
        )

    def __unicode__(self):
        return '{} preprint (guid={}) of {}'.format('published' if self.is_published else 'unpublished', self._id, self.node.__unicode__() if self.node else None)

    @property
    def verified_publishable(self):
        return self.is_published and self.node.is_preprint and not self.node.is_deleted

    @property
    def primary_file(self):
        if not self.node:
            return
        return self.node.preprint_file

    @property
    def is_retracted(self):
        return self.date_withdrawn is not None

    @property
    def article_doi(self):
        if not self.node:
            return
        return self.node.preprint_article_doi

    @property
    def preprint_doi(self):
        return self.get_identifier_value('doi')

    @property
    def is_preprint_orphan(self):
        if not self.node:
            return
        return self.node.is_preprint_orphan

    @property
    def deep_url(self):
        # Required for GUID routing
        return '/preprints/{}/'.format(self._primary_key)

    @property
    def url(self):
        if (self.provider.domain_redirect_enabled and self.provider.domain) or self.provider._id == 'osf':
            return '/{}/'.format(self._id)

        return '/preprints/{}/{}/'.format(self.provider._id, self._id)

    @property
    def absolute_url(self):
        return urlparse.urljoin(
            self.provider.domain if self.provider.domain_redirect_enabled else settings.DOMAIN,
            self.url
        )

    @property
    def absolute_api_v2_url(self):
        path = '/preprints/{}/'.format(self._id)
        return api_v2_url(path)

    def has_permission(self, *args, **kwargs):
        return self.node.has_permission(*args, **kwargs)

    def set_primary_file(self, preprint_file, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s primary file.')

        if preprint_file.node != self.node or preprint_file.provider != 'osfstorage':
            raise ValueError('This file is not a valid primary file for this preprint.')

        existing_file = self.node.preprint_file
        self.node.preprint_file = preprint_file

        # only log if updating the preprint file, not adding for the first time
        if existing_file:
            self.node.add_log(
                action=NodeLog.PREPRINT_FILE_UPDATED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False
            )

        if save:
            self.save()
            self.node.save()

    def set_published(self, published, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can publish a preprint.')

        if self.is_published and not published:
            raise ValueError('Cannot unpublish preprint.')

        self.is_published = published

        if published:
            if not (self.node.preprint_file and self.node.preprint_file.node == self.node):
                raise ValueError('Preprint node is not a valid preprint; cannot publish.')
            if not self.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.subjects.exists():
                raise ValueError('Preprint must have at least one subject to be published.')
            self.date_published = timezone.now()
            self.node._has_abandoned_preprint = False

            # In case this provider is ever set up to use a reviews workflow, put this preprint in a sensible state
            self.machine_state = ReviewStates.ACCEPTED.value
            self.date_last_transitioned = self.date_published

            # This preprint will have a tombstone page when it's withdrawn.
            self.ever_public = True

            self.node.add_log(
                action=NodeLog.PREPRINT_INITIATED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False,
            )

            if not self.node.is_public:
                self.node.set_privacy(
                    self.node.PUBLIC,
                    auth=None,
                    log=True
                )

            self._send_preprint_confirmation(auth)

        if save:
            self.node.save()
            self.save()

    def set_preprint_license(self, license_detail, auth, save=False):
        license_record, license_changed = set_license(self, license_detail, auth, node_type='preprint')

        if license_changed:
            self.node.add_log(
                action=NodeLog.PREPRINT_LICENSE_UPDATED,
                params={
                    'preprint': self._id,
                    'new_license': license_record.node_license.name
                },
                auth=auth,
                save=False
            )

        if save:
            self.save()

    def set_identifier_values(self, doi, save=False):
        self.set_identifier_value('doi', doi)
        self.preprint_doi_created = timezone.now()

        if save:
            self.save()

    def get_doi_client(self):
        if settings.CROSSREF_URL:
            if self.provider._id == 'ecsarxiv':
                return ECSArXivCrossRefClient(base_url=settings.CROSSREF_URL)
            return CrossRefClient(base_url=settings.CROSSREF_URL)
        else:
            return None

    def save(self, *args, **kwargs):
        first_save = not bool(self.pk)
        saved_fields = self.get_dirty_fields() or []
        old_subjects = kwargs.pop('old_subjects', [])
        if saved_fields:
            request, user_id = get_request_and_user_id()
            request_headers = {}
            if not isinstance(request, DummyRequest):
                request_headers = {
                    k: v
                    for k, v in get_headers_from_request(request).items()
                    if isinstance(v, basestring)
                }
            user = OSFUser.load(user_id)
            if user:
                self.check_spam(user, saved_fields, request_headers)
        if not first_save and ('ever_public' in saved_fields and saved_fields['ever_public']):
            raise ValidationError('Cannot set "ever_public" to False')

        ret = super(PreprintService, self).save(*args, **kwargs)

        if (not first_save and 'is_published' in saved_fields) or self.is_published:
            enqueue_postcommit_task(on_preprint_updated, (self._id,), {'old_subjects': old_subjects}, celery=True)
        return ret

    def _get_spam_content(self, saved_fields):
        spam_fields = self.SPAM_CHECK_FIELDS if self.is_published and 'is_published' in saved_fields else self.SPAM_CHECK_FIELDS.intersection(
            saved_fields)
        content = []
        for field in spam_fields:
            content.append((getattr(self.node, field, None) or '').encode('utf-8'))
        if self.node.all_tags.exists():
            content.extend(map(lambda name: name.encode('utf-8'), self.node.all_tags.values_list('name', flat=True)))
        if not content:
            return None
        return ' '.join(content)

    def check_spam(self, user, saved_fields, request_headers):
        if not settings.SPAM_CHECK_ENABLED:
            return False
        if settings.SPAM_CHECK_PUBLIC_ONLY and not self.node.is_public:
            return False
        if 'ham_confirmed' in user.system_tags:
            return False

        content = self._get_spam_content(saved_fields)
        if not content:
            return
        is_spam = self.do_check_spam(
            user.fullname,
            user.username,
            content,
            request_headers,
        )
        logger.info("Preprint ({}) '{}' smells like {} (tip: {})".format(
            self._id, self.node.title.encode('utf-8'), 'SPAM' if is_spam else 'HAM', self.spam_pro_tip
        ))
        if is_spam:
            self.node._check_spam_user(user)
        return is_spam

    def _check_spam_user(self, user):
        self.node._check_spam_user(user)

    def flag_spam(self):
        """ Overrides SpamMixin#flag_spam.
        """
        super(PreprintService, self).flag_spam()
        self.node.flag_spam()

    def confirm_spam(self, save=False):
        super(PreprintService, self).confirm_spam(save=save)
        self.node.confirm_spam(save=save)

    def _send_preprint_confirmation(self, auth):
        # Send creator confirmation email
        recipient = self.node.creator
        event_type = utils.find_subscription_type('global_reviews')
        user_subscriptions = get_user_subscriptions(recipient, event_type)
        if self.provider._id == 'osf':
            logo = settings.OSF_PREPRINTS_LOGO
        else:
            logo = self.provider._id

        context = {
            'domain': settings.DOMAIN,
            'reviewable': self,
            'workflow': self.provider.reviews_workflow,
            'provider_url': '{domain}preprints/{provider_id}'.format(
                            domain=self.provider.domain or settings.DOMAIN,
                            provider_id=self.provider._id if not self.provider.domain else '').strip('/'),
            'provider_contact_email': self.provider.email_contact or settings.OSF_CONTACT_EMAIL,
            'provider_support_email': self.provider.email_support or settings.OSF_SUPPORT_EMAIL,
            'no_future_emails': user_subscriptions['none'],
            'is_creator': True,
            'provider_name': 'OSF Preprints' if self.provider.name == 'Open Science Framework' else self.provider.name,
            'logo': logo,
        }

        mails.send_mail(
            recipient.username,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            mimetype='html',
            user=recipient,
            **context
        )
