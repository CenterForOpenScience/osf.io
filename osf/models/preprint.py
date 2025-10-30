import functools
import inspect
from urllib.parse import urljoin
import logging
import re

from dirtyfields import DirtyFieldsMixin
from django.db import models, IntegrityError
from django.db.models import Q, Max
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import get_objects_for_user
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save

from framework import sentry
from framework.auth import Auth
from framework.exceptions import PermissionsError, UnpublishedPendingPreprintVersionExists
from framework.auth import oauth_scopes

from .subject import Subject
from .tag import Tag
from .user import OSFUser
from .provider import PreprintProvider
from .preprintlog import PreprintLog
from .contributor import PreprintContributor
from .mixins import ReviewableMixin, Taggable, Loggable, GuardianMixin, AffiliatedInstitutionMixin
from .validators import validate_doi
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
from website.util.metrics import provider_source_tag
from website.citations.utils import datetime_to_csl
from website import settings, mails
from website.preprints.tasks import update_or_enqueue_on_preprint_updated

from .base import BaseModel, Guid, GuidVersionsThrough, GuidMixinQuerySet, VersionedGuidMixin, check_manually_assigned_guid
from .identifiers import IdentifierMixin, Identifier
from .mixins import TaxonomizableMixin, ContributorMixin, SpamOverrideMixin, TitleMixin, DescriptionMixin
from addons.osfstorage.models import OsfStorageFolder, Region, BaseFileNode, OsfStorageFile

from framework.sentry import log_exception
from osf.exceptions import (
    PreprintStateError,
    InvalidTagError,
    TagNotFoundError,
    UserStateError,
    ValidationValueError,
)
from django.contrib.postgres.fields import ArrayField
from api.share.utils import update_share

logger = logging.getLogger(__name__)


class PreprintManager(models.Manager):
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

    def preprint_versions_permissions_query(self, user=None, allow_contribs=True, public_only=False):
        include_non_public = user and not user.is_anonymous and not public_only
        if include_non_public:
            moderator_for = get_objects_for_user(user, 'view_submissions', PreprintProvider, with_superuser=False)
            admin_user_query = Q(id__in=get_objects_for_user(user, 'admin_preprint', self.filter(Q(preprintcontributor__user_id=user.id)), with_superuser=False))
            reviews_user_query = Q(is_public=True, provider__in=moderator_for)
            if allow_contribs:
                contrib_user_query = ~Q(
                    machine_state__in=[
                        DefaultStates.PENDING.value,
                        DefaultStates.REJECTED.value
                    ]
                ) & Q(id__in=get_objects_for_user(user, 'read_preprint', self.filter(Q(preprintcontributor__user_id=user.id)), with_superuser=False))
                query = (self.no_user_query | contrib_user_query | admin_user_query | reviews_user_query)
            else:
                query = (self.no_user_query | admin_user_query | reviews_user_query)
        else:
            moderator_for = PreprintProvider.objects.none()
            query = self.no_user_query

        if not moderator_for.exists():
            query = query & Q(Q(date_withdrawn__isnull=True) | Q(ever_public=True))
        return query & ~Q(machine_state=DefaultStates.INITIAL.value)

class PublishedPreprintManager(PreprintManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)

class RejectedPreprintManager(PreprintManager):
    def get_queryset(self):
        return super().get_queryset().filter(actions__to_state='rejected')

class EverPublishedPreprintManager(PreprintManager):
    def get_queryset(self):
        return super().get_queryset().filter(date_published__isnull=False)


def require_permission(permissions: list):
    """
    Preprint-specific decorator for permission checks.

    This decorator adds an implicit `ignore_permission` argument to the decorated function,
    allowing you to bypass the permission check when set to `True`.

    Usage example:
        preprint.some_method(..., ignore_permission=True)  # Skips permission check
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, ignore_permission=False, **kwargs):
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(self, *args, **kwargs)
            bound_args.apply_defaults()

            auth = bound_args.arguments.get('auth', None)

            if not ignore_permission and auth is not None:
                for permission in permissions:
                    if not self.has_permission(auth.user, permission):
                        raise PermissionsError(f'Must have following permissions to change a preprint: {permissions}')
            return func(self, *args, ignore_permission=ignore_permission, **kwargs)
        return wrapper
    return decorator


class Preprint(DirtyFieldsMixin, VersionedGuidMixin, IdentifierMixin, ReviewableMixin, BaseModel, TitleMixin, DescriptionMixin,
        Loggable, Taggable, ContributorMixin, GuardianMixin, SpamOverrideMixin, TaxonomizableMixin, AffiliatedInstitutionMixin):

    objects = PreprintManager()
    published_objects = PublishedPreprintManager()
    ever_published_objects = EverPublishedPreprintManager()
    rejected_objects = RejectedPreprintManager()
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
        'date_withdrawn',
        'withdrawal_justification'
    }

    PREREG_LINK_INFO_CHOICES = [('prereg_designs', 'Pre-registration of study designs'),
                                ('prereg_analysis', 'Pre-registration of study analysis'),
                                ('prereg_both', 'Pre-registration of study designs and study analysis')
                                ]

    HAS_LINKS_CHOICES = [('available', 'Available'),
                         ('no', 'No'),
                         ('not_applicable', 'Not applicable')
                         ]

    # overrides AffiliatedInstitutionMixin
    affiliated_institutions = models.ManyToManyField('Institution', related_name='preprints')

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
    custom_publication_citation = models.TextField(null=True, blank=True)
    license = models.ForeignKey('osf.NodeLicenseRecord',
                                on_delete=models.SET_NULL, null=True, blank=True)

    identifiers = GenericRelation(Identifier, related_query_name='preprints')
    preprint_doi_created = NonNaiveDateTimeField(default=None, null=True, blank=True)
    date_withdrawn = NonNaiveDateTimeField(default=None, null=True, blank=True)
    withdrawal_justification = models.TextField(default='', blank=True)
    ever_public = models.BooleanField(default=False, blank=True)
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
    primary_file = models.ForeignKey(
        'osf.OsfStorageFile',
        null=True,
        blank=True,
        related_name='preprint',
        on_delete=models.CASCADE
    )
    # (for legacy preprints), pull off of node
    is_public = models.BooleanField(default=True, db_index=True)
    # Datetime when old node was deleted (for legacy preprints)
    deleted = NonNaiveDateTimeField(null=True, blank=True)
    # For legacy preprints
    migrated = NonNaiveDateTimeField(null=True, blank=True)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.CASCADE)

    # For ContributorMixin
    guardian_object_type = 'preprint'

    READ_PREPRINT = f'read_{guardian_object_type}'
    WRITE_PREPRINT = f'write_{guardian_object_type}'
    ADMIN_PREPRINT = f'admin_{guardian_object_type}'

    # For ContributorMixin
    base_perms = [READ_PREPRINT, WRITE_PREPRINT, ADMIN_PREPRINT]

    # For GuardianMixin
    groups = {
        'read': (READ_PREPRINT,),
        'write': (READ_PREPRINT, WRITE_PREPRINT,),
        'admin': (READ_PREPRINT, WRITE_PREPRINT, ADMIN_PREPRINT,)
    }
    # For GuardianMixin
    group_format = 'preprint_{self.id}_{group}'

    conflict_of_interest_statement = models.TextField(
        blank=True,
        null=True,
    )
    has_coi = models.BooleanField(
        blank=True,
        null=True
    )
    has_prereg_links = models.TextField(
        choices=HAS_LINKS_CHOICES,
        null=True,
        blank=True
    )
    why_no_prereg = models.TextField(
        null=True,
        blank=True
    )
    prereg_links = ArrayField(
        models.URLField(
            null=True,
            blank=True
        ),
        blank=True,
        null=True
    )
    prereg_link_info = models.TextField(
        choices=PREREG_LINK_INFO_CHOICES,
        null=True,
        blank=True
    )
    has_data_links = models.TextField(
        choices=HAS_LINKS_CHOICES,
        null=True,
        blank=True
    )
    why_no_data = models.TextField(
        null=True,
        blank=True
    )
    data_links = ArrayField(
        models.URLField(
            null=True,
            blank=True
        ),
        blank=True,
        null=True
    )

    class Meta:
        permissions = (
            # Clashes with built-in permissions
            # ('view_preprint', 'Can view preprint details in the admin app'),
            ('read_preprint', 'Can read the preprint'),
            ('write_preprint', 'Can write the preprint'),
            ('admin_preprint', 'Can manage the preprint'),
        )

    def __unicode__(self):
        return '{} ({} preprint) (guid={}){}'.format(self.title, 'published' if self.is_published else 'unpublished', self._id, ' with supplemental files on ' + self.node.__unicode__() if self.node else '')

    @classmethod
    def create(cls, provider, title, creator, description, manual_guid=None, manual_doi=None):
        """Customized creation process to support preprint versions and versioned guid.
        """
        # Step 1: Create the preprint obj
        preprint = cls(
            provider=provider,
            title=title,
            creator=creator,
            description=description,
        )
        preprint.save(guid_ready=False)
        # Step 2: Create the base guid obj
        if manual_guid:
            if not check_manually_assigned_guid(manual_guid):
                raise ValidationError(f'GUID cannot be manually assigned: guid_str={manual_guid}.')
            base_guid_obj = Guid.objects.create(_id=manual_guid)
        else:
            base_guid_obj = Guid.objects.create()
        base_guid_obj.referent = preprint
        base_guid_obj.object_id = preprint.pk
        base_guid_obj.content_type = ContentType.objects.get_for_model(preprint)
        base_guid_obj.save()
        # Step 3: Create a new entry in the `GuidVersionsThrough` table to store version information
        versioned_guid = GuidVersionsThrough(
            referent=base_guid_obj.referent,
            object_id=base_guid_obj.object_id,
            content_type=base_guid_obj.content_type,
            version=VersionedGuidMixin.INITIAL_VERSION_NUMBER,
            guid=base_guid_obj
        )
        versioned_guid.save()
        preprint.save(guid_ready=True, first_save=True)
        if manual_doi:
            preprint.set_identifier_values(manual_doi, save=True)

        return preprint

    def get_last_not_rejected_version(self):
        """Get the last version that is not rejected.
        """
        return self.get_guid().versions.filter(is_rejected=False).order_by('-version').first().referent

    def has_unpublished_pending_version(self):
        """Check if preprint has pending unpublished version.
        Note: use `.check_unfinished_or_unpublished_version()` if checking both types
        """
        last_not_rejected_version = self.get_last_not_rejected_version()
        return not last_not_rejected_version.date_published and last_not_rejected_version.machine_state == 'pending'

    def has_initiated_but_unfinished_version(self):
        """Check if preprint has initiated but unfinished version.
        Note: use `.check_unfinished_or_unpublished_version()` if checking both types
        """
        last_not_rejected_version = self.get_last_not_rejected_version()
        return not last_not_rejected_version.date_published and last_not_rejected_version.machine_state == 'initial'

    def check_unfinished_or_unpublished_version(self):
        """Check and return the "initiated but unfinished version" and "unfinished or unpublished version".
        """
        last_not_rejected_version = self.get_last_not_rejected_version()
        if last_not_rejected_version.date_published:
            return None, None
        if last_not_rejected_version.machine_state == 'initial':
            return last_not_rejected_version, None
        if last_not_rejected_version.machine_state == 'pending':
            return None, last_not_rejected_version
        return None, None

    @classmethod
    def create_version(cls, create_from_guid, auth, assign_version_number=None, ignore_permission=False, ignore_existing_versions=False):
        """Create a new version for a given preprint. `create_from_guid` can be any existing versions of the preprint
        but `create_version` always finds the latest version and creates a new version from it. In addition, this
        creates an "incomplete" new preprint version object using the model class and returns both the new object and
        the data to be updated. The API, more specifically `PreprintCreateVersionSerializer` must call `.update()` to
        "completely finish" the new preprint version object creation.
        Optionally, you can assign a custom version number, as long as it doesn't conflict with existing versions.
        The version must be an integer greater than 0.
        """

        # Use `Guid.load()` instead of `VersionedGuid.load()` to retrieve the base guid obj, which always points to the
        # latest (ever-published) version.
        guid_obj = Guid.load(create_from_guid)
        latest_version = cls.load(guid_obj._id)
        if not latest_version:
            sentry.log_message(f'Preprint not found: [guid={guid_obj._id}, create_from_guid={create_from_guid}]')
            return None, None
        if not ignore_permission and not latest_version.has_permission(auth.user, ADMIN):
            sentry.log_message(f'ADMIN permission for the latest version is required to create a new version: '
                               f'[user={auth.user._id}, guid={guid_obj._id}, latest_version={latest_version._id}]')
            raise PermissionsError
        if not ignore_existing_versions:
            unfinished_version, unpublished_version = latest_version.check_unfinished_or_unpublished_version()
            if unpublished_version:
                message = ('Failed to create a new version due to unpublished pending version already exists: '
                            f'[version={unpublished_version.version}, '
                            f'_id={unpublished_version._id}, '
                            f'state={unpublished_version.machine_state}].')
                logger.error(message)
                raise UnpublishedPendingPreprintVersionExists(message)
            if unfinished_version:
                logger.warning(f'Use existing initiated but unfinished version instead of creating a new one: '
                            f'[version={unfinished_version.version}, '
                            f'_id={unfinished_version._id}, '
                            f'state={unfinished_version.machine_state}].')
                return unfinished_version, None

        # Prepare the data to clone/update
        data_to_update = {
            'subjects': [el for el in latest_version.subjects.all().values_list('_id', flat=True)],
            'tags': latest_version.tags.all().values_list('name', flat=True),
            'original_publication_date': latest_version.original_publication_date,
            'custom_publication_citation': latest_version.custom_publication_citation,
            'article_doi': latest_version.article_doi, 'has_coi': latest_version.has_coi,
            'conflict_of_interest_statement': latest_version.conflict_of_interest_statement,
            'has_data_links': latest_version.has_data_links, 'why_no_data': latest_version.why_no_data,
            'data_links': latest_version.data_links,
            'has_prereg_links': latest_version.has_prereg_links,
            'why_no_prereg': latest_version.why_no_prereg, 'prereg_links': latest_version.prereg_links,
        }
        if latest_version.license:
            data_to_update['license_type'] = latest_version.license.node_license
            data_to_update['license'] = {
                'copyright_holders': latest_version.license.copyright_holders,
                'year': latest_version.license.year
            }

        # Create a preprint obj for the new version
        preprint = cls(
            provider=latest_version.provider,
            title=latest_version.title,
            creator=auth.user,
            description=latest_version.description,
        )
        preprint.save(guid_ready=False)

        # Note: version number bumps from the last version number instead of the latest version number
        # if assign_version_number is not specified
        if assign_version_number:
            if not isinstance(assign_version_number, int) or assign_version_number <= 0:
                raise ValueError(
                    f"Unable to assign: {assign_version_number}. "
                    'Version must be integer greater than 0.'
                )
            if GuidVersionsThrough.objects.filter(guid=guid_obj, version=assign_version_number).first():
                raise ValueError(f"Version {assign_version_number} for preprint {guid_obj} already exists.")

            version_number = assign_version_number
        else:
            last_version_number = guid_obj.versions.order_by('-version').first().version
            version_number = last_version_number + 1

        # Create a new entry in the `GuidVersionsThrough` table to store version information, which must happen right
        # after the first `.save()` of the new preprint version object, which enables `preprint._id` to be computed.
        guid_version = GuidVersionsThrough(
            referent=preprint,
            object_id=guid_obj.object_id,
            content_type=guid_obj.content_type,
            version=version_number,
            guid=guid_obj
        )
        guid_version.save()
        preprint.save(guid_ready=True, first_save=True, set_creator_as_contributor=False)

        # Add contributors
        for contributor in latest_version.contributor_set.all():
            try:
                preprint.add_contributor(
                    contributor.user,
                    permissions=contributor.permission,
                    visible=contributor.visible,
                    save=True
                )
            except (ValidationValueError, UserStateError) as e:
                sentry.log_exception(e)
                sentry.log_message(f'Contributor was not added to new preprint version due to error: '
                                   f'[preprint={preprint._id}, user={contributor.user._id}]')

        # Add new version record for unregistered contributors
        for contributor in preprint.contributor_set.filter(Q(user__is_registered=False) | Q(user__date_disabled__isnull=False)):
            try:
                contributor.user.add_unclaimed_record(
                    claim_origin=preprint,
                    referrer=auth.user,
                    email=contributor.user.email,
                    given_name=contributor.user.fullname,
                )
            except ValidationError as e:
                sentry.log_exception(e)
                sentry.log_message(f'Unregistered contributor was not added to new preprint version due to error: '
                                   f'[preprint={preprint._id}, user={contributor.user._id}]')

        # Add affiliated institutions
        for institution in latest_version.affiliated_institutions.all():
            preprint.add_affiliated_institution(institution, auth.user, ignore_user_affiliation=True)

        # Update Guid obj to point to the new version if there is no moderation and new version is bigger
        if not preprint.provider.reviews_workflow and version_number > guid_obj.referent.version:
            guid_obj.referent = preprint
            guid_obj.object_id = preprint.pk
            guid_obj.content_type = ContentType.objects.get_for_model(preprint)
            guid_obj.save()

        if latest_version.node:
            preprint.set_supplemental_node(
                latest_version.node,
                auth,
                save=False,
                ignore_node_permissions=True,
                ignore_permission=ignore_permission
            )

        return preprint, data_to_update

    def upgrade_version(self):
        """Increase preprint version by one."""
        guid_version = GuidVersionsThrough.objects.get(object_id=self.id)
        guid_version.version += 1
        guid_version.save()

        return self

    @property
    def is_deleted(self):
        return bool(self.deleted)

    @is_deleted.setter
    def is_deleted(self, val):
        """Set whether or not this preprint has been deleted."""
        if val and not self.deleted:
            self.deleted = timezone.now()
        elif val is False:
            self.deleted = None

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
            'preprint': self._id,
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
    def is_pending_moderation(self):
        if self.machine_state == DefaultStates.INITIAL.value:
            return False

        if not self.provider or not self.provider.reviews_workflow:
            return False

        from api.providers.workflows import PUBLIC_STATES

        workflow = self.provider.reviews_workflow
        public_states = PUBLIC_STATES.get(workflow, [])

        if self.machine_state not in public_states:
            return True

        return False

    @property
    def deep_url(self):
        # Required for GUID routing
        return f'/preprints/{self._id}/'

    @property
    def url(self):
        if (self.provider.domain_redirect_enabled and self.provider.domain) or self.provider._id == 'osf':
            return f'/{self._id}/'

        return f'/preprints/{self.provider._id}/{self._id}/'

    @property
    def absolute_url(self):
        return urljoin(
            self.provider.domain if self.provider.domain_redirect_enabled else settings.DOMAIN,
            self.url
        )

    @property
    def absolute_api_v2_url(self):
        path = f'/preprints/{self._id}/'
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
    def institutions_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/institutions/'

    @property
    def admin_contributor_or_group_member_ids(self):
        # Overrides ContributorMixin
        # Preprints don't have parents or group members at the moment, so this is just admin group member ids
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

    @property
    def is_latest_version(self):
        return self.guids.exists()

    @property
    def date_created_first_version(self):
        try:
            base_guid = self.versioned_guids.first().guid if self.versioned_guids.exists() else None
            if not base_guid:
                return self.created

            first_version = base_guid.versions.filter(is_rejected=False).order_by('version').first()

            if first_version and first_version.referent:
                return first_version.referent.created

            return self.created
        except Exception:
            return self.created

    def get_preprint_versions(self, include_rejected=True, **version_filters):
        guids = self.versioned_guids.first().guid.versions.all()
        preprint_versions = (
            Preprint.objects
            .filter(id__in=[vg.object_id for vg in guids], **version_filters)
            .annotate(latest_version=Max('versioned_guids__version'))
            .order_by('-latest_version')
        )
        if include_rejected is False:
            preprint_versions = preprint_versions.exclude(machine_state=DefaultStates.REJECTED.value)
        return preprint_versions

    def web_url_for(self, view_name, _absolute=False, _guid=False, *args, **kwargs):
        return web_url_for(view_name, pid=self._id,
                           _absolute=_absolute, _guid=_guid, *args, **kwargs)

    def api_url_for(self, view_name, _absolute=False, *args, **kwargs):
        return api_url_for(view_name, pid=self._id, _absolute=_absolute, *args, **kwargs)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def add_log(self, action, params, auth, foreign_user=None, log_date=None, save=True, request=None, should_hide=False):
        user = None
        if auth:
            user = auth.user
        elif request:
            user = request.user

        params['preprint'] = params.get('preprint') or self._id

        log = PreprintLog(
            action=action, user=user, foreign_user=foreign_user,
            params=params, preprint=self, should_hide=should_hide
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

    @require_permission([WRITE])
    def set_primary_file(self, preprint_file, auth, save=False, **kwargs):
        if not self.root_folder:
            raise PreprintStateError('Preprint needs a root folder.')

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

    @require_permission([ADMIN])
    def set_published(self, published, auth, save=False, **kwargs):
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
            self.set_privacy('public', log=False, save=False, **kwargs)

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

    @require_permission([WRITE])
    def set_preprint_license(self, license_detail, auth, save=False, **kwargs):
        license_record, license_changed = set_license(self, license_detail, auth, node_type='preprint', **kwargs)

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

    def full_clean(self):
        super().full_clean()
        if self.article_doi and self.provider:
            expected_doi = settings.DOI_FORMAT.format(prefix=self.provider.doi_prefix, guid=self._id)
            if expected_doi.startswith(self.article_doi):
                raise ValidationError({
                    'article_doi': (
                        f'The `article_doi` "{expected_doi}" is already associated with this preprint; '
                        'please enter a peer-reviewed publication\'s DOI.'
                    )
                })

    def save(self, *args, **kwargs):
        """Customize preprint save process, which has three steps.

        1. Initial: this save happens before guid and versioned guid are created for the preprint; this save
        creates the pk; after this save, none of `guids`, `versioned_guids` or `._id` is available.
        2. First: this save happens and must happen right after versioned guid have been created; this is the
        same "first save" as it was before preprint became versioned; the only change is that `pk` already exists
        3. This is the case for all subsequent saves after initial and first save.

        Note: When creating a preprint or new version , must use Preprint.create() or Preprint.create_version()
        respectively, which handles the save process automatically.
        """
        initial_save = not kwargs.pop('guid_ready', True)
        if initial_save:
            # Save when guid and versioned guid are not ready
            return super().save(*args, **kwargs)

        # Preprint must have PK and _id set before continue
        if not bool(self.pk):
            err_msg = 'Preprint must have pk!'
            sentry.log_message(err_msg)
            raise IntegrityError(err_msg)
        if not self._id:
            err_msg = 'Preprint must have _id!'
            sentry.log_message(err_msg)
            raise IntegrityError(err_msg)

        first_save = kwargs.pop('first_save', False)
        set_creator_as_contributor = kwargs.pop('set_creator_as_contributor', True)
        saved_fields = self.get_dirty_fields() or []

        if not first_save and ('ever_public' in saved_fields and saved_fields['ever_public']):
            raise ValidationError('Cannot set "ever_public" to False')
        if self.has_submitted_preprint and not self.primary_file:
            raise ValidationError('Cannot save non-initial preprint without primary file.')

        ret = super().save(*args, **kwargs)

        if saved_fields and (not settings.SPAM_CHECK_PUBLIC_ONLY or self.verified_publishable):
            request, user_id = get_request_and_user_id()
            request_headers = string_type_request_headers(request)
            user = OSFUser.load(user_id)
            if user:
                self.check_spam(user, saved_fields, request_headers)

        if first_save:
            self._set_default_region()
            self.update_group_permissions()
            # exception is a new preprint version because we must inherit contributors ordering from the last version
            # thus no need to set creator as the first contributor immediately
            if set_creator_as_contributor:
                self._add_creator_as_contributor()

        if (not first_save and 'is_published' in saved_fields) or self.is_published:
            update_or_enqueue_on_preprint_updated(preprint_id=self._id, saved_fields=saved_fields)
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
            'document_type': self.provider.preprint_word
        }

        mails.send_mail(
            recipient.username,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
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
    def system_tags_objects(self):
        return self.all_tags.filter(system=True)

    @property
    def system_tags(self):
        """The system tags associated with this node. This currently returns a list of string
        names for the tags, for compatibility with v1. Eventually, we can just return the
        QuerySet.
        """
        return self.system_tags_objects.values_list('name', flat=True)

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

        tag_obj = self.tags.filter(name=tag).first() or self.all_tags.filter(name=tag).first()
        if not tag_obj:
            raise TagNotFoundError

        if tag_obj.system:
            # because system tags are hidden by default TagManager
            tag_obj.delete()
        else:
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

    @require_permission([WRITE])
    def set_supplemental_node(self, node, auth, save=False, ignore_node_permissions=False, **kwargs):
        if not node.has_permission(auth.user, WRITE) and not ignore_node_permissions:
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

    @require_permission([WRITE])
    def unset_supplemental_node(self, auth, save=False, **kwargs):
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

    @require_permission([WRITE])
    def set_title(self, title, auth, save=False, **kwargs):
        """Set the title of this Preprint and log it.

        :param str title: The new title.
        :param auth: All the auth information including user, API key.
        """
        return super().set_title(title, auth, save)

    @require_permission([WRITE])
    def set_description(self, description, auth, save=False, **kwargs):
        """Set the description and log the event.

        :param str description: The new description
        :param auth: All the auth informtion including user, API key.
        :param bool save: Save self after updating.
        """
        return super().set_description(description, auth, save)

    def get_spam_fields(self, saved_fields=None):
        if not saved_fields or (self.is_published and 'is_published' in saved_fields):
            return self.SPAM_CHECK_FIELDS
        return self.SPAM_CHECK_FIELDS.intersection(saved_fields)

    @require_permission([WRITE])
    def set_privacy(self, permissions, auth=None, log=True, save=True, check_addons=False, force=False, should_hide=False, **kwargs):
        """Set the permissions for this preprint - mainly for spam purposes.

        :param permissions: A string, either 'public' or 'private'
        :param auth: All the auth information including user, API key.
        :param bool log: Whether to add a NodeLog for the privacy change.
        :param bool meeting_creation: Whether this was created due to a meetings email.
        :param bool check_addons: Check and collect messages for addons?
        """
        if permissions == 'public' and not self.is_public:
            if (self.is_spam or (settings.SPAM_FLAGGED_MAKE_NODE_PRIVATE and self.is_spammy)) and not force:
                raise PreprintStateError(
                    'This preprint has been marked as spam. Please contact the help desk if you think this is in error.'
                )
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
                should_hide=should_hide
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
        for _preprint in preprints:
            if _preprint.is_latest_version:
                update_share(_preprint)
        from website import search
        try:
            serialize = functools.partial(search.search.update_preprint, index=index, bulk=True, async_update=False)
            search.search.bulk_update_nodes(serialize, preprints, index=index)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception(e)

    def update_search(self):
        # Only update share if the preprint is the latest version (i.e. has `guids`)
        if self.is_latest_version:
            update_share(self)
        from website import search
        try:
            search.search.update_preprint(self, bulk=False, async_update=True)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception(e)

    def serialize_waterbutler_settings(self, provider_name=None):
        """
        Since preprints don't have addons, this method has been pulled over from the
        OSFStorage addon
        """
        if provider_name and provider_name != 'osfstorage':
            raise ValueError('Preprints only have access to osfstorage')
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
        if provider_name and provider_name != 'osfstorage':
            raise ValueError('Preprints only have access to osfstorage')
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
            f'osf_storage_{action}',
            auth=Auth(user),
            params=params
        )

    # Overrides ContributorMixin
    def _add_related_source_tags(self, contributor):
        system_tag_to_add, created = Tag.all_tags.get_or_create(name=provider_source_tag(self.provider._id, 'preprint'), system=True)
        contributor.add_system_tag(system_tag_to_add)

    @require_permission([ADMIN])
    def update_has_coi(self, auth: Auth, has_coi: bool, log: bool = True, save: bool = True, **kwargs):
        """
        This method sets the field `has_coi` to indicate if there's a conflict interest statement for this preprint
        and logs that change.

        :param auth: Auth object
        :param has_coi: Boolean represents if a user has a conflict of interest statement available.
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if has_coi is None:
            has_coi = False

        if self.has_coi == has_coi:
            return

        self.has_coi = has_coi

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_HAS_COI,
                params={
                    'user': auth.user._id,
                    'value': self.has_coi
                },
                auth=auth,
            )
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_conflict_of_interest_statement(self, auth: Auth, coi_statement: str, log: bool = True, save: bool = True, **kwargs):
        """
        This method sets the `conflict_of_interest_statement` field for this preprint and logs that change.

        :param auth: Auth object
        :param coi_statement: String represents a user's conflict of interest statement for their preprint.
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if self.conflict_of_interest_statement == coi_statement:
            return

        self.conflict_of_interest_statement = coi_statement or ''

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_COI_STATEMENT,
                params={
                    'user': auth.user._id,
                    'value': self.conflict_of_interest_statement
                },
                auth=auth,
            )
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_has_data_links(self, auth: Auth, has_data_links: bool, log: bool = True, save: bool = True, **kwargs):
        """
        This method sets the `has_data_links` field that respresent the availability of links to supplementary data
        for this preprint and logs that change.

        :param auth: Auth object
        :param has_data_links: Boolean represents the availability of links to supplementary data for this preprint
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if self.has_data_links == has_data_links:
            return

        if has_data_links == 'no':
            self.data_links = []

        self.has_data_links = has_data_links

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_HAS_DATA_LINKS,
                params={
                    'user': auth.user._id,
                    'value': has_data_links
                },
                auth=auth
            )
        if not has_data_links:
            self.update_data_links(auth, data_links=[], log=False, **kwargs)
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_data_links(self, auth: Auth, data_links: list, log: bool = True, save: bool = True, **kwargs):
        """
        This method sets the field `data_links` which is a validated list of links to supplementary data for a
        preprint and logs that change.

        :param auth: Auth object
        :param data_links: List urls that should link to supplementary data for a preprint.
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if self.data_links == data_links:
            return

        if not self.has_data_links and data_links:
            self.data_links = []

        self.data_links = data_links

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_DATA_LINKS,
                params={
                    'user': auth.user._id,
                },
                auth=auth
            )
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_why_no_data(self, auth: Auth, why_no_data: str, log: bool = True, save: bool = True, **kwargs):
        """
        This method sets the field `why_no_data` a string that represents a user provided explanation for the
        unavailability of supplementary data for their preprint.

        :param auth: Auth object
        :param why_no_data: String a user provided explanation for the unavailability of data links for their preprint.
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if self.why_no_data == why_no_data:
            return

        if self.has_data_links:
            self.why_no_data = ''

        self.why_no_data = why_no_data

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_WHY_NO_DATA,
                params={
                    'user': auth.user._id,
                },
                auth=auth
            )
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_has_prereg_links(self, auth: Auth, has_prereg_links: bool, log: bool = True, save: bool = True, **kwargs):
        """
        This method updates the `has_prereg_links` field, that indicates availability of links to prereg data and logs
        changes to it.

        :param auth: Auth object
        :param has_prereg_links: Boolean indicates whether the user has links to preregistration materials
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if has_prereg_links == self.has_prereg_links:
            return

        if has_prereg_links == 'no':
            self.prereg_links = []
            self.prereg_link_info = None

        self.has_prereg_links = has_prereg_links

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_HAS_PREREG_LINKS,
                params={
                    'user': auth.user._id,
                    'value': has_prereg_links
                },
                auth=auth
            )
        if not has_prereg_links:
            self.update_prereg_links(auth, prereg_links=[], log=False, **kwargs)
            self.update_prereg_link_info(auth, prereg_link_info=None, log=False, **kwargs)
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_why_no_prereg(self, auth: Auth, why_no_prereg: str, log: bool = True, save: bool = True, **kwargs):
        """
        This method updates the field `why_no_prereg` that contains a user provided explanation of prereg data
        unavailability and logs changes to it.

        :param auth: Auth object
        :param why_no_prereg: String explanation of prereg data unavailability
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if why_no_prereg == self.why_no_prereg:
            return

        if self.has_prereg_links or self.has_prereg_links is None:
            self.why_no_prereg = ''

        self.why_no_prereg = why_no_prereg

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_WHY_NO_PREREG,
                params={
                    'user': auth.user._id,
                },
                auth=auth
            )
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_prereg_links(self, auth: Auth, prereg_links: list, log: bool = True, save: bool = True, **kwargs):
        """
        This method updates the field `prereg_links` that contains a list of validated URLS linking to prereg data
        and logs changes to it.

        :param auth: Auth object
        :param prereg_links: List list of validated urls with schemes to links to prereg data
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if prereg_links == self.prereg_links:
            return

        if not self.has_prereg_links and prereg_links:
            self.prereg_links = []

        self.prereg_links = prereg_links

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_PREREG_LINKS,
                params={
                    'user': auth.user._id,
                },
                auth=auth
            )
        if save:
            self.save()

    @require_permission([ADMIN])
    def update_prereg_link_info(self, auth: Auth, prereg_link_info: str, log: bool = True, save: bool = True, **kwargs):
        """
        This method updates the field `prereg_link_info` that contains a one of a finite number of choice strings in
        contained in the list in the static member `PREREG_LINK_INFO_CHOICES` that describe the nature of the preprint's
        prereg links.

        :param auth: Auth object
        :param prereg_link_info: String a string describing the nature of the preprint's prereg links.
        :param log: Boolean should this be logged?
        :param save: Boolean should this be saved immediately?
        :return:

        This method brought to you via a grant from the Alfred P Sloan Foundation.
        """
        if self.prereg_link_info == prereg_link_info:
            return

        if not self.has_prereg_links and prereg_link_info:
            self.prereg_link_info = None

        self.prereg_link_info = prereg_link_info

        if log:
            self.add_log(
                action=PreprintLog.UPDATE_PREREG_LINKS_INFO,
                params={
                    'user': auth.user._id,
                },
                auth=auth
            )
        if save:
            self.save()

    def run_submit(self, user):
        """Override `ReviewableMixin`/`MachineableMixin`.
        Run the 'submit' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
        """
        ret = super().run_submit(user=user)

        base_guid_obj = self.versioned_guids.first().guid
        base_guid_obj.referent = self
        base_guid_obj.object_id = self.pk
        base_guid_obj.content_type = ContentType.objects.get_for_model(self)
        base_guid_obj.save()

        return ret

    def run_accept(self, user, comment, **kwargs):
        """Override `ReviewableMixin`/`MachineableMixin`.
        Run the 'accept' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        ret = super().run_accept(user=user, comment=comment, **kwargs)
        versioned_guid = self.versioned_guids.first()
        if versioned_guid.is_rejected:
            versioned_guid.is_rejected = False
            versioned_guid.save()
        return ret

    def run_reject(self, user, comment):
        """Override `ReviewableMixin`/`MachineableMixin`.
        Run the 'reject' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        ret = super().run_reject(user=user, comment=comment)
        current_version_guid = self.versioned_guids.first()
        current_version_guid.is_rejected = True
        current_version_guid.save()

        self.rollback_main_guid()

        return ret

    def rollback_main_guid(self):
        """Reset main guid to resolve to last versioned guid which is not withdrawn/rejected if there is one.
        """
        guid = None
        for version in self.versioned_guids.all()[1:]:  # skip first guid as it refers to current version
            guid = version.guid
            if guid.referent.machine_state not in (ReviewStates.REJECTED, ReviewStates.WITHDRAWN):
                break
        if guid:
            guid.referent = self
            guid.object_id = self.pk
            guid.content_type = ContentType.objects.get_for_model(self)
            guid.save()

    def run_withdraw(self, user, comment):
        """Override `ReviewableMixin`/`MachineableMixin`.
        Run the 'withdraw' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        ret = super().run_withdraw(user=user, comment=comment)
        self.rollback_main_guid()
        return ret

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
