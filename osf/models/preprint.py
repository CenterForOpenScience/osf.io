# -*- coding: utf-8 -*-
import functools
from future.moves.urllib.parse import urljoin
import logging
import re

from dirtyfields import DirtyFieldsMixin
from include import IncludeManager
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import get_objects_for_user, get_group_perms
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import AnonymousUser
from django.db.models.signals import post_save

from framework.auth import Auth
from framework.exceptions import PermissionsError
from framework.auth import oauth_scopes

from osf.models import Subject, Tag, OSFUser, PreprintProvider
from osf.models.preprintlog import PreprintLog
from osf.models.contributor import PreprintContributor
from osf.models.mixins import ReviewableMixin, Taggable, Loggable, GuardianMixin
from osf.models.validators import validate_title, validate_doi
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.workflows import DefaultStates, ReviewStates
from osf.utils import sanitize
from osf.utils.permissions import ADMIN, WRITE
from osf.utils.requests import get_request_and_user_id, string_type_request_headers
from website.notifications.emails import get_user_subscriptions
from website.notifications import utils
from website.identifiers.clients import CrossRefClient, ECSArXivCrossRefClient
from website.project.licenses import set_license
from website.util import api_v2_url, api_url_for, web_url_for
from website.citations.utils import datetime_to_csl
from website import settings, mails
from website.preprints.tasks import update_or_enqueue_on_preprint_updated

from osf.models.base import BaseModel, GuidMixin, GuidMixinQuerySet
from osf.models.identifiers import IdentifierMixin, Identifier
from osf.models.mixins import TaxonomizableMixin, ContributorMixin, SpamOverrideMixin
from addons.osfstorage.models import OsfStorageFolder, Region, BaseFileNode, OsfStorageFile


from framework.sentry import log_exception
from osf.exceptions import (
    PreprintStateError, InvalidTagError, TagNotFoundError
)

logger = logging.getLogger(__name__)


class PreprintManager(IncludeManager):
    def get_queryset(self):
        return GuidMixinQuerySet(self.model, using=self._db)

    no_user_query = Q(
        is_published=True,
        is_public=True,
        deleted__isnull=True,
        primary_file__isnull=False,
        primary_file__deleted_on__isnull=True) & ~Q(machine_state=DefaultStates.INITIAL.value) \
        & (Q(date_withdrawn__isnull=True) | Q(ever_public=True))

    def preprint_permissions_query(self, user=None, allow_contribs=True, public_only=False):
        include_non_public = user and not user.is_anonymous and not public_only
        if include_non_public:
            moderator_for = get_objects_for_user(user, 'view_submissions', PreprintProvider, with_superuser=False)
            admin_user_query = Q(id__in=get_objects_for_user(user, 'admin_preprint', self.filter(Q(preprintcontributor__user_id=user.id)), with_superuser=False))
            reviews_user_query = Q(is_public=True, provider__in=moderator_for)
            if allow_contribs:
                contrib_user_query = ~Q(machine_state=DefaultStates.INITIAL.value) & Q(id__in=get_objects_for_user(user, 'read_preprint', self.filter(Q(preprintcontributor__user_id=user.id)), with_superuser=False))
                query = (self.no_user_query | contrib_user_query | admin_user_query | reviews_user_query)
            else:
                query = (self.no_user_query | admin_user_query | reviews_user_query)
        else:
            moderator_for = PreprintProvider.objects.none()
            query = self.no_user_query

        if not moderator_for.exists():
            query = query & Q(Q(date_withdrawn__isnull=True) | Q(ever_public=True))
        return query

    def can_view(self, base_queryset=None, user=None, allow_contribs=True, public_only=False):
        if base_queryset is None:
            base_queryset = self
        include_non_public = user and not public_only
        ret = base_queryset.filter(
            self.preprint_permissions_query(
                user=user,
                allow_contribs=allow_contribs,
                public_only=public_only,
            ) & Q(deleted__isnull=True) & ~Q(machine_state=DefaultStates.INITIAL.value)
        )
        # The auth subquery currently results in duplicates returned
        # https://openscience.atlassian.net/browse/OSF-9058
        # TODO: Remove need for .distinct using correct subqueries
        return ret.distinct('id', 'created') if include_non_public else ret


class Preprint(DirtyFieldsMixin, GuidMixin, IdentifierMixin, ReviewableMixin, BaseModel,
        Loggable, Taggable, GuardianMixin, SpamOverrideMixin, TaxonomizableMixin, ContributorMixin):

    objects = PreprintManager()
    # Preprint fields that trigger a check to the spam filter on save
    SPAM_CHECK_FIELDS = {
        'title',
        'description',
    }

    # Node fields that trigger an update to elastic search on save
    SEARCH_UPDATE_FIELDS = {
        'title',
        'description',
        'is_published',
        'license',
        'is_public',
        'deleted',
        'subjects',
        'primary_file',
        'contributors',
        'tags',
    }

    provider = models.ForeignKey('osf.PreprintProvider',
                                 on_delete=models.SET_NULL,
                                 related_name='preprints',
                                 null=True, blank=True, db_index=True)
    node = models.ForeignKey('osf.AbstractNode', on_delete=models.SET_NULL,
                             related_name='preprints',
                             null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    date_published = NonNaiveDateTimeField(null=True, blank=True)
    original_publication_date = NonNaiveDateTimeField(null=True, blank=True)
    license = models.ForeignKey('osf.NodeLicenseRecord',
                                on_delete=models.SET_NULL, null=True, blank=True)

    identifiers = GenericRelation(Identifier, related_query_name='preprints')
    preprint_doi_created = NonNaiveDateTimeField(default=None, null=True, blank=True)
    date_withdrawn = NonNaiveDateTimeField(default=None, null=True, blank=True)
    withdrawal_justification = models.TextField(default='', blank=True)
    ever_public = models.BooleanField(default=False, blank=True)
    title = models.TextField(
        validators=[validate_title]
    )  # this should be a charfield but data from mongo didn't fit in 255
    description = models.TextField(blank=True, default='')
    creator = models.ForeignKey(OSFUser,
                                db_index=True,
                                related_name='preprints_created',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    _contributors = models.ManyToManyField(OSFUser,
                                           through=PreprintContributor,
                                           related_name='preprints')
    article_doi = models.CharField(max_length=128,
                                            validators=[validate_doi],
                                            null=True, blank=True)
    files = GenericRelation('osf.OsfStorageFile', object_id_field='target_object_id', content_type_field='target_content_type')
    primary_file = models.ForeignKey('osf.OsfStorageFile', null=True, blank=True, related_name='preprint')
    # (for legacy preprints), pull off of node
    is_public = models.BooleanField(default=True, db_index=True)
    # Datetime when old node was deleted (for legacy preprints)
    deleted = NonNaiveDateTimeField(null=True, blank=True)
    # For legacy preprints
    migrated = NonNaiveDateTimeField(null=True, blank=True)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.CASCADE)
    groups = {
        'read': ('read_preprint',),
        'write': ('read_preprint', 'write_preprint',),
        'admin': ('read_preprint', 'write_preprint', 'admin_preprint',)
    }
    group_format = 'preprint_{self.id}_{group}'

    class Meta:
        permissions = (
            ('view_preprint', 'Can view preprint details in the admin app'),
            ('read_preprint', 'Can read the preprint'),
            ('write_preprint', 'Can write the preprint'),
            ('admin_preprint', 'Can manage the preprint'),
        )

    def __unicode__(self):
        return '{} ({} preprint) (guid={}){}'.format(self.title, 'published' if self.is_published else 'unpublished', self._id, ' with supplemental files on ' + self.node.__unicode__() if self.node else '')

    @property
    def is_deleted(self):
        return bool(self.deleted)

    @property
    def root_folder(self):
        try:
            return OsfStorageFolder.objects.get(name='', target_object_id=self.id, target_content_type_id=ContentType.objects.get_for_model(Preprint).id, is_root=True)
        except BaseFileNode.DoesNotExist:
            return None

    @property
    def osfstorage_region(self):
        return self.region

    @property
    def contributor_email_template(self):
        return 'preprint'

    @property
    def file_read_scope(self):
        return oauth_scopes.CoreScopes.PREPRINT_FILE_READ

    @property
    def file_write_scope(self):
        return oauth_scopes.CoreScopes.PREPRINT_FILE_WRITE

    @property
    def visible_contributors(self):
        # Overrides ContributorMixin
        return OSFUser.objects.filter(
            preprintcontributor__preprint=self,
            preprintcontributor__visible=True
        ).order_by('preprintcontributor___order')

    @property
    def log_class(self):
        # Property needed for ContributorMixin
        return PreprintLog

    @property
    def contributor_class(self):
        # Property needed for ContributorMixin
        return PreprintContributor

    @property
    def contributor_kwargs(self):
        # Property needed for ContributorMixin
        return {
            'preprint': self
        }

    @property
    def order_by_contributor_field(self):
        # Property needed for ContributorMixin
        return 'preprintcontributor___order'

    @property
    def log_params(self):
        # Property needed for ContributorMixin
        return {
            'preprint': self._id
        }

    @property
    def contributor_set(self):
        # Property needed for ContributorMixin
        return self.preprintcontributor_set

    @property
    def state_error(self):
        # Property needed for ContributorMixin
        return PreprintStateError

    @property
    def is_retracted(self):
        return self.date_withdrawn is not None

    @property
    def verified_publishable(self):
        return self.is_published and \
            self.is_public and \
            self.has_submitted_preprint and not \
            self.deleted and not \
            self.is_preprint_orphan and not \
            (self.is_retracted and not self.ever_public)

    @property
    def should_request_identifiers(self):
        return not self.all_tags.filter(name='qatest').exists()

    @property
    def has_pending_withdrawal_request(self):
        return self.requests.filter(request_type='withdrawal', machine_state='pending').exists()

    @property
    def has_withdrawal_request(self):
        return self.requests.filter(request_type='withdrawal').exists()

    @property
    def preprint_doi(self):
        return self.get_identifier_value('doi')

    @property
    def is_preprint_orphan(self):
        if not self.primary_file_id:
            return True

        try:
            primary_file = self.primary_file
        except OsfStorageFile.DoesNotExist:
            primary_file = None

        if not primary_file or primary_file.deleted_on or primary_file.target != self:
            return True

        return False

    @property
    def has_submitted_preprint(self):
        return self.machine_state != DefaultStates.INITIAL.value

    @property
    def deep_url(self):
        # Required for GUID routing
        return '/preprints/{}/'.format(self._id)

    @property
    def url(self):
        if (self.provider.domain_redirect_enabled and self.provider.domain) or self.provider._id == 'osf':
            return '/{}/'.format(self._id)

        return '/preprints/{}/{}/'.format(self.provider._id, self._id)

    @property
    def absolute_url(self):
        return urljoin(
            self.provider.domain if self.provider.domain_redirect_enabled else settings.DOMAIN,
            self.url
        )

    @property
    def absolute_api_v2_url(self):
        path = '/preprints/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    @property
    def linked_nodes_self_url(self):
        return self.absolute_api_v2_url + 'relationships/node/'

    @property
    def admin_contributor_or_group_member_ids(self):
        # Overrides ContributorMixin
        # Preprints don't have parents or group members at the moment, so we override here.
        # Called when removing project subscriptions
        return self.get_group(ADMIN).user_set.filter(is_active=True).values_list('guids___id', flat=True)

    @property
    def csl(self):  # formats node information into CSL format for citation parsing
        """a dict in CSL-JSON schema

        For details on this schema, see:
            https://github.com/citation-style-language/schema#csl-json-schema
        """
        csl = {
            'id': self._id,
            'title': sanitize.unescape_entities(self.title),
            'author': [
                contributor.csl_name(self._id)  # method in auth/model.py which parses the names of authors
                for contributor in self.visible_contributors
            ],
            'type': 'webpage',
            'URL': self.display_absolute_url,
            'publisher': 'OSF Preprints' if self.provider.name == 'Open Science Framework' else self.provider.name
        }

        article_doi = self.article_doi
        preprint_doi = self.preprint_doi

        if article_doi:
            csl['DOI'] = article_doi
        elif preprint_doi and self.is_published and self.preprint_doi_created:
            csl['DOI'] = preprint_doi

        if self.date_published:
            csl['issued'] = datetime_to_csl(self.date_published)

        return csl

    def web_url_for(self, view_name, _absolute=False, _guid=False, *args, **kwargs):
        return web_url_for(view_name, pid=self._id,
                           _absolute=_absolute, _guid=_guid, *args, **kwargs)

    def api_url_for(self, view_name, _absolute=False, *args, **kwargs):
        return api_url_for(view_name, pid=self._id, _absolute=_absolute, *args, **kwargs)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def add_log(self, action, params, auth, foreign_user=None, log_date=None, save=True, request=None):
        user = None
        if auth:
            user = auth.user
        elif request:
            user = request.user

        params['preprint'] = params.get('preprint') or self._id

        log = PreprintLog(
            action=action, user=user, foreign_user=foreign_user,
            params=params, preprint=self
        )

        log.save()

        self._complete_add_log(log, action, user, save)
        return log

    def can_view_files(self, auth=None):
        if self.is_retracted:
            return False

        if not auth or not auth.user:
            return self.verified_publishable
        else:
            return self.can_view(auth=auth)

    def get_addons(self):
        # Override for ContributorMixin, Preprints don't have addons
        return []

    def add_subjects_log(self, old_subjects, auth):
        # Overrides TaxonomizableMixin
        self.add_log(
            action=PreprintLog.SUBJECTS_UPDATED,
            params={
                'subjects': list(self.subjects.values('_id', 'text')),
                'old_subjects': list(Subject.objects.filter(id__in=old_subjects).values('_id', 'text')),
                'preprint': self._id
            },
            auth=auth,
            save=False,
        )
        return

    def set_primary_file(self, preprint_file, auth, save=False):
        if not self.root_folder:
            raise PreprintStateError('Preprint needs a root folder.')

        if not self.has_permission(auth.user, WRITE):
            raise PermissionsError('Must have admin or write permissions to change a preprint\'s primary file.')

        if preprint_file.target != self or preprint_file.provider != 'osfstorage':
            raise ValueError('This file is not a valid primary file for this preprint.')

        existing_file = self.primary_file
        self.primary_file = preprint_file

        self.primary_file.move_under(self.root_folder)
        self.primary_file.save()

        # only log if updating the preprint file, not adding for the first time
        if existing_file:
            self.add_log(
                action=PreprintLog.FILE_UPDATED,
                params={
                    'preprint': self._id,
                    'file': self.primary_file._id
                },
                auth=auth,
                save=False
            )

        if save:
            self.save()
        update_or_enqueue_on_preprint_updated(preprint_id=self._id, saved_fields=['primary_file'])

    def set_published(self, published, auth, save=False):
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can publish a preprint.')

        if self.is_published and not published:
            raise ValueError('Cannot unpublish preprint.')

        self.is_published = published

        if published:
            if not self.title:
                raise ValueError('Preprint needs a title; cannot publish.')
            if not (self.primary_file and self.primary_file.target == self):
                raise ValueError('Preprint is not a valid preprint; cannot publish.')
            if not self.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.subjects.exists():
                raise ValueError('Preprint must have at least one subject to be published.')
            self.date_published = timezone.now()
            # For legacy preprints, not logging
            self.set_privacy('public', log=False, save=False)

            # In case this provider is ever set up to use a reviews workflow, put this preprint in a sensible state
            self.machine_state = ReviewStates.ACCEPTED.value
            self.date_last_transitioned = self.date_published

            # This preprint will have a tombstone page when it's withdrawn.
            self.ever_public = True

            self.add_log(
                action=PreprintLog.PUBLISHED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False,
            )
            self._send_preprint_confirmation(auth)

        if save:
            self.save()

    def set_preprint_license(self, license_detail, auth, save=False):
        license_record, license_changed = set_license(self, license_detail, auth, node_type='preprint')

        if license_changed:
            self.add_log(
                action=PreprintLog.CHANGED_LICENSE,
                params={
                    'preprint': self._id,
                    'new_license': license_record.node_license.name
                },
                auth=auth,
                save=False
            )
        if save:
            self.save()
        update_or_enqueue_on_preprint_updated(preprint_id=self._id, saved_fields=['license'])

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
            request_headers = string_type_request_headers(request)
            user = OSFUser.load(user_id)
            if user:
                self.check_spam(user, saved_fields, request_headers)

        if not first_save and ('ever_public' in saved_fields and saved_fields['ever_public']):
            raise ValidationError('Cannot set "ever_public" to False')

        ret = super(Preprint, self).save(*args, **kwargs)

        if first_save:
            self._set_default_region()
            self.update_group_permissions()
            self._add_creator_as_contributor()

        if (not first_save and 'is_published' in saved_fields) or self.is_published:
            update_or_enqueue_on_preprint_updated(preprint_id=self._id, old_subjects=old_subjects, saved_fields=saved_fields)
        return ret

    def update_or_enqueue_on_resource_updated(self, user_id, first_save, saved_fields):
        # Needed for ContributorMixin
        return update_or_enqueue_on_preprint_updated(preprint_id=self._id, saved_fields=saved_fields)

    def _set_default_region(self):
        user_settings = self.creator.get_addon('osfstorage')
        self.region_id = user_settings.default_region_id
        self.save()

    def _add_creator_as_contributor(self):
        self.add_contributor(self.creator, permissions=ADMIN, visible=True, log=False, save=True)

    def _send_preprint_confirmation(self, auth):
        # Send creator confirmation email
        recipient = self.creator
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

    # FOLLOWING BEHAVIOR NOT SPECIFIC TO PREPRINTS

    @property
    def all_tags(self):
        """Return a queryset containing all of this node's tags (incl. system tags)."""
        # Tag's default manager only returns non-system tags, so we can't use self.tags
        return Tag.all_tags.filter(preprint_tagged=self)

    @property
    def system_tags(self):
        """The system tags associated with this node. This currently returns a list of string
        names for the tags, for compatibility with v1. Eventually, we can just return the
        QuerySet.
        """
        return self.all_tags.filter(system=True).values_list('name', flat=True)

    # Override Taggable
    def add_tag_log(self, tag, auth):
        self.add_log(
            action=PreprintLog.TAG_ADDED,
            params={
                'preprint': self._id,
                'tag': tag.name
            },
            auth=auth,
            save=False
        )

    # Override Taggable
    def on_tag_added(self, tag):
        update_or_enqueue_on_preprint_updated(preprint_id=self._id, saved_fields=['tags'])

    def remove_tag(self, tag, auth, save=True):
        if not tag:
            raise InvalidTagError
        elif not self.tags.filter(name=tag).exists():
            raise TagNotFoundError
        else:
            tag_obj = Tag.objects.get(name=tag)
            self.tags.remove(tag_obj)
            self.add_log(
                action=PreprintLog.TAG_REMOVED,
                params={
                    'preprint': self._id,
                    'tag': tag,
                },
                auth=auth,
                save=False,
            )
            if save:
                self.save()
            update_or_enqueue_on_preprint_updated(preprint_id=self._id, saved_fields=['tags'])
            return True

    def set_supplemental_node(self, node, auth, save=False):
        if not self.has_permission(auth.user, WRITE):
            raise PermissionsError('You must have write permissions to set a supplemental node.')

        if not node.has_permission(auth.user, WRITE):
            raise PermissionsError('You must have write permissions on the supplemental node to attach.')

        if node.is_deleted:
            raise ValueError('Cannot attach a deleted project to a preprint.')

        self.node = node

        self.add_log(
            action=PreprintLog.SUPPLEMENTAL_NODE_ADDED,
            params={
                'preprint': self._id,
                'node': self.node._id,
            },
            auth=auth,
            save=False,
        )

        if save:
            self.save()

    def unset_supplemental_node(self, auth, save=False):
        if not self.has_permission(auth.user, WRITE):
            raise PermissionsError('You must have write permissions to set a supplemental node.')

        current_node_id = self.node._id if self.node else None
        self.node = None

        self.add_log(
            action=PreprintLog.SUPPLEMENTAL_NODE_REMOVED,
            params={
                'preprint': self._id,
                'node': current_node_id
            },
            auth=auth,
            save=False,
        )

        if save:
            self.save()

    def set_title(self, title, auth, save=False):
        """Set the title of this Node and log it.

        :param str title: The new title.
        :param auth: All the auth information including user, API key.
        """
        if not self.has_permission(auth.user, WRITE):
            raise PermissionsError('Must have admin or write permissions to edit a preprint\'s title.')

        # Called so validation does not have to wait until save.
        validate_title(title)

        original_title = self.title
        new_title = sanitize.strip_html(title)
        # Title hasn't changed after sanitzation, bail out
        if original_title == new_title:
            return False
        self.title = new_title
        self.add_log(
            action=PreprintLog.EDITED_TITLE,
            params={
                'preprint': self._id,
                'title_new': self.title,
                'title_original': original_title,
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        return None

    def set_description(self, description, auth, save=False):
        """Set the description and log the event.

        :param str description: The new description
        :param auth: All the auth informtion including user, API key.
        :param bool save: Save self after updating.
        """
        if not self.has_permission(auth.user, WRITE):
            raise PermissionsError('Must have admin or write permissions to edit a preprint\'s title.')

        original = self.description
        new_description = sanitize.strip_html(description)
        if original == new_description:
            return False
        self.description = new_description
        self.add_log(
            action=PreprintLog.EDITED_DESCRIPTION,
            params={
                'preprint': self._id,
                'description_new': self.description,
                'description_original': original
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        return None

    def get_spam_fields(self, saved_fields):
        return self.SPAM_CHECK_FIELDS if self.is_published and 'is_published' in saved_fields else self.SPAM_CHECK_FIELDS.intersection(
            saved_fields)

    def get_permissions(self, user):
        # Overrides guardian mixin - doesn't return view_preprint perms, and
        # returns readable perms instead of literal perms
        if isinstance(user, AnonymousUser):
            return []
        perms = ['read_preprint', 'write_preprint', 'admin_preprint']
        user_perms = sorted(set(get_group_perms(user, self)).intersection(perms), key=perms.index)
        return [perm.split('_')[0] for perm in user_perms]

    def set_privacy(self, permissions, auth=None, log=True, save=True, check_addons=False):
        """Set the permissions for this preprint - mainly for spam purposes.

        :param permissions: A string, either 'public' or 'private'
        :param auth: All the auth information including user, API key.
        :param bool log: Whether to add a NodeLog for the privacy change.
        :param bool meeting_creation: Whether this was created due to a meetings email.
        :param bool check_addons: Check and collect messages for addons?
        """
        if auth and not self.has_permission(auth.user, WRITE):
            raise PermissionsError('Must have admin or write permissions to change privacy settings.')
        if permissions == 'public' and not self.is_public:
            if self.is_spam or (settings.SPAM_FLAGGED_MAKE_NODE_PRIVATE and self.is_spammy):
                # TODO: Should say will review within a certain agreed upon time period.
                raise PreprintStateError('This preprint has been marked as spam. Please contact the help desk if you think this is in error.')
            self.is_public = True
        elif permissions == 'private' and self.is_public:
            self.is_public = False
        else:
            return False

        if log:
            action = PreprintLog.MADE_PUBLIC if permissions == 'public' else PreprintLog.MADE_PRIVATE
            self.add_log(
                action=action,
                params={
                    'preprint': self._id,
                },
                auth=auth,
                save=False,
            )
        if save:
            self.save()
        return True

    def can_view(self, auth):
        if not auth.user:
            return self.verified_publishable

        return (self.verified_publishable or
            (self.is_public and auth.user.has_perm('view_submissions', self.provider)) or
            self.has_permission(auth.user, ADMIN) or
            (self.is_contributor(auth.user) and self.has_submitted_preprint)
        )

    def can_edit(self, auth=None, user=None):
        """Return if a user is authorized to edit this preprint.
        Must specify one of (`auth`, `user`).

        :param Auth auth: Auth object to check
        :param User user: User object to check
        :returns: Whether user has permission to edit this node.
        """
        if not auth and not user:
            raise ValueError('Must pass either `auth` or `user`')
        if auth and user:
            raise ValueError('Cannot pass both `auth` and `user`')
        user = user or auth.user

        return (
            user and ((self.has_permission(user, WRITE) and self.has_submitted_preprint) or self.has_permission(user, ADMIN))
        )

    def get_contributor_order(self):
        # Method needed for ContributorMixin
        return self.get_preprintcontributor_order()

    def set_contributor_order(self, contributor_ids):
        # Method needed for ContributorMixin
        return self.set_preprintcontributor_order(contributor_ids)

    @classmethod
    def bulk_update_search(cls, preprints, index=None):
        from website import search
        try:
            serialize = functools.partial(search.search.update_preprint, index=index, bulk=True, async_update=False)
            search.search.bulk_update_nodes(serialize, preprints, index=index)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def update_search(self):
        from website import search
        try:
            search.search.update_preprint(self, bulk=False, async_update=True)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def serialize_waterbutler_settings(self, provider_name=None):
        """
        Since preprints don't have addons, this method has been pulled over from the
        OSFStorage addon
        """
        return dict(Region.objects.get(id=self.region_id).waterbutler_settings, **{
            'nid': self._id,
            'rootId': self.root_folder._id,
            'baseUrl': api_url_for(
                'osfstorage_get_metadata',
                guid=self._id,
                _absolute=True,
                _internal=True
            )
        })

    def serialize_waterbutler_credentials(self, provider_name=None):
        """
        Since preprints don't have addons, this method has been pulled over from the
        OSFStorage addon
        """
        return Region.objects.get(id=self.region_id).waterbutler_credentials

    def create_waterbutler_log(self, auth, action, payload):
        """
        Since preprints don't have addons, this method has been pulled over from the
        OSFStorage addon
        """
        metadata = payload['metadata']
        user = auth.user
        params = {
            'preprint': self._id,
            'path': metadata['materialized'],
        }
        if (metadata['kind'] != 'folder'):
            url = self.web_url_for(
                'addon_view_or_download_file',
                guid=self._id,
                path=metadata['path'],
                provider='osfstorage'
            )
            params['urls'] = {'view': url, 'download': url + '?action=download'}

        self.add_log(
            'osf_storage_{0}'.format(action),
            auth=Auth(user),
            params=params
        )


@receiver(post_save, sender=Preprint)
def create_file_node(sender, instance, **kwargs):
    if instance.root_folder:
        return
    # Note: The "root" node will always be "named" empty string
    root_folder = OsfStorageFolder(name='', target=instance, is_root=True)
    root_folder.save()


class PreprintUserObjectPermission(UserObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - User models - we typically add object
    perms directly to Django groups instead of users, so this will be used infrequently
    """
    content_object = models.ForeignKey(Preprint, on_delete=models.CASCADE)

class PreprintGroupObjectPermission(GroupObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - Group models. Makes permission checks faster.

    This table gives a Django group a particular permission to a Preprint.
    For example, every time a preprint is created, an admin, write, and read Django group
    are created for the preprint. The "write" group has write/read perms to the preprint.

    Those links are stored here:  content_object_id (preprint_id), group_id, permission_id
    """
    content_object = models.ForeignKey(Preprint, on_delete=models.CASCADE)
