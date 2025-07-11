import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlencode
import uuid
from copy import deepcopy

from flask import Request as FlaskRequest
from framework import analytics
from guardian.shortcuts import get_perms

# OSF imports
import itsdangerous
import pytz
from dirtyfields import DirtyFieldsMixin

from django.apps import apps
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import PermissionsMixin
from django.dispatch import receiver
from django.db import models
from django.db.models import Count, Exists, OuterRef
from django.db.models.signals import post_save
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user

from framework import sentry
from framework.auth import Auth, signals, utils
from framework.auth.core import generate_verification_key
from framework.auth.exceptions import (
    ChangePasswordError,
    ExpiredTokenError,
    InvalidTokenError,
    MergeConfirmedRequiredError,
)
from framework.exceptions import PermissionsError
from framework.sessions.utils import remove_sessions_for_user
from osf.external.gravy_valet import (
    request_helpers as gv_requests,
    translations as gv_translations,
)
from osf.utils.requests import get_current_request
from osf.exceptions import reraise_django_validation_errors, UserStateError
from .base import BaseModel, GuidMixin, GuidMixinQuerySet
from .notable_domain import NotableDomain
from .contributor import Contributor, RecentlyAddedContributor
from .institution import Institution
from .institution_affiliation import InstitutionAffiliation
from .mixins import AddonModelMixin
from .spam import SpamMixin
from .session import UserSessionMap
from .tag import Tag
from .validators import validate_email, validate_social, validate_history_item
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField, LowercaseEmailField, ensure_str
from osf.utils.names import impute_names
from osf.utils.requests import check_select_for_update
from osf.utils.permissions import API_CONTRIBUTOR_PERMISSIONS, MANAGER, MEMBER, MANAGE, ADMIN
from website import settings as website_settings
from website import filters, mails
from website.project import new_bookmark_collection
from website.util.metrics import OsfSourceTags, unregistered_created_source_tag
from importlib import import_module
from osf.utils.requests import get_headers_from_request

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

logger = logging.getLogger(__name__)

MAX_QUICKFILES_MERGE_RENAME_ATTEMPTS = 1000


def get_default_mailing_lists():
    return {'Open Science Framework Help': True}


name_formatters = {
    'long': lambda user: user.fullname,
    'surname': lambda user: user.family_name if user.family_name else user.fullname,
    'initials': lambda user: f'{user.family_name}, {user.given_name_initial}.',
}


class OSFUserManager(BaseUserManager):

    def create_user(self, username, password=None):
        if not username:
            raise ValueError('Users must have a username')

        user = self.model(
            username=self.normalize_email(username),
            is_active=True,
            date_registered=timezone.now()
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    _queryset_class = GuidMixinQuerySet

    def all(self):
        return self.get_queryset().all()

    def eager(self, *fields):
        fk_fields = set(self.model.get_fk_field_names()) & set(fields)
        m2m_fields = set(self.model.get_m2m_field_names()) & set(fields)
        return self.select_related(*fk_fields).prefetch_related(*m2m_fields)

    def create_superuser(self, username, password):
        user = self.create_user(username, password=password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user


class Email(BaseModel):
    address = LowercaseEmailField(unique=True, db_index=True, validators=[validate_email])
    user = models.ForeignKey('OSFUser', related_name='emails', on_delete=models.CASCADE)

    def __unicode__(self):
        return self.address


class OSFUser(DirtyFieldsMixin, GuidMixin, BaseModel, AbstractBaseUser, PermissionsMixin, AddonModelMixin, SpamMixin):
    FIELD_ALIASES = {
        '_id': 'guids___id',
        'system_tags': 'tags',
    }
    settings_type = 'user'  # Needed for addons
    USERNAME_FIELD = 'username'

    # Node fields that trigger an update to the search engine on save
    SEARCH_UPDATE_FIELDS = {
        'fullname',
        'given_name',
        'middle_names',
        'family_name',
        'suffix',
        'merged_by',
        'date_disabled',
        'date_confirmed',
        'jobs',
        'schools',
        'social',
        'allow_indexing',
    }

    # Overrides DirtyFieldsMixin, Foreign Keys checked by '<attribute_name>_id' rather than typical name.
    FIELDS_TO_CHECK = SEARCH_UPDATE_FIELDS.copy()
    FIELDS_TO_CHECK.update({'password', 'last_login', 'merged_by_id', 'username'})

    # TODO: Add SEARCH_UPDATE_NODE_FIELDS, for fields that should trigger a
    #   search update for all nodes to which the user is a contributor.

    SOCIAL_FIELDS = {
        'orcid': 'http://orcid.org/{}',
        'github': 'http://github.com/{}',
        'scholar': 'http://scholar.google.com/citations?user={}',
        'twitter': 'http://twitter.com/{}',
        'profileWebsites': [],
        'linkedIn': 'https://www.linkedin.com/{}',
        'impactStory': 'https://impactstory.org/u/{}',
        'researcherId': 'http://researcherid.com/rid/{}',
        'researchGate': 'https://researchgate.net/profile/{}',
        'academiaInstitution': 'https://{}',
        'academiaProfileID': '.academia.edu/{}',
        'baiduScholar': 'http://xueshu.baidu.com/scholarID/{}',
        'ssrn': 'http://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id={}'
    }

    SPAM_USER_PROFILE_FIELDS = {
        'schools': ['degree', 'institution', 'department'],
        'jobs': ['title', 'institution', 'department'],
        'social': ['profileWebsites'],
    }
    # Normalized form of the SPAM_USER_PROFILE_FIELDS to match other SPAM_CHECK_FIELDS formats
    SPAM_CHECK_FIELDS = [
        'social__profileWebsites'
    ]

    # The primary email address for the account.
    # This value is unique, but multiple "None" records exist for:
    #   * unregistered contributors where an email address was not provided.
    # TODO: Update mailchimp subscription on username change in user.save()
    # TODO: Consider making this a FK to Email with to_field='address'
    #   Django supports this (https://docs.djangoproject.com/en/1.11/topics/auth/customizing/#django.contrib.auth.models.CustomUser.USERNAME_FIELD)
    #   but some third-party apps may not.
    username = models.CharField(max_length=255, db_index=True, unique=True)

    # Hashed. Use `User.set_password` and `User.check_password`
    # password = models.CharField(max_length=255)

    fullname = models.CharField(max_length=255)

    # user has taken action to register the account
    is_registered = models.BooleanField(db_index=True, default=False)

    # for internal use
    tags = models.ManyToManyField('Tag', blank=True)

    # security emails that have been sent
    # TODO: This should be removed and/or merged with system_tags
    security_messages = DateTimeAwareJSONField(default=dict, blank=True)
    # Format: {
    #   <message label>: <datetime>
    #   ...
    # }

    # user was invited (as opposed to registered unprompted)
    is_invited = models.BooleanField(default=False, db_index=True)

    # Per-project unclaimed user data:
    # TODO: add validation
    unclaimed_records = DateTimeAwareJSONField(default=dict, blank=True)
    # Format: {
    #   <project_id>: {
    #       'name': <name that referrer provided>,
    #       'referrer_id': <user ID of referrer>,
    #       'token': <token used for verification urls>,
    #       'email': <email the referrer provided or None>,
    #       'claimer_email': <email the claimer entered or None>,
    #       'last_sent': <timestamp of last email sent to referrer or None>
    #   }
    #   ...
    # }

    # Time of last sent notification email to newly added contributors
    # Format : {
    #   <project_id>: {
    #       'last_sent': time.time()
    #   }
    #   ...
    # }
    contributor_added_email_records = DateTimeAwareJSONField(default=dict, blank=True)

    # Tracks last email sent where user was added to an OSF Group
    member_added_email_records = DateTimeAwareJSONField(default=dict, blank=True)
    # Tracks last email sent where an OSF Group was connected to a node
    group_connected_email_records = DateTimeAwareJSONField(default=dict, blank=True)

    # The user into which this account was merged
    merged_by = models.ForeignKey('self', null=True, blank=True, related_name='merger', on_delete=models.CASCADE)

    # verification key v1: only the token string, no expiration time
    # used for cas login with username and verification key
    verification_key = models.CharField(max_length=255, null=True, blank=True)

    # verification key v2: token, and expiration time
    # used for password reset, confirm account/email, claim account/contributor-ship
    verification_key_v2 = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    # Format: {
    #   'token': <verification token>
    #   'expires': <verification expiration time>
    # }

    email_last_sent = NonNaiveDateTimeField(null=True, blank=True)
    change_password_last_attempt = NonNaiveDateTimeField(null=True, blank=True)
    # Logs number of times user attempted to change their password where their
    # old password was invalid
    old_password_invalid_attempts = models.PositiveIntegerField(default=0)

    # email verification tokens
    #   see also ``unconfirmed_emails``
    email_verifications = DateTimeAwareJSONField(default=dict, blank=True)
    # Format: {
    #   <token> : {'email': <email address>,
    #              'expiration': <datetime>}
    # }

    # email lists to which the user has chosen a subscription setting
    mailchimp_mailing_lists = DateTimeAwareJSONField(default=dict, blank=True)
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # email lists to which the user has chosen a subscription setting,
    # being sent from osf, rather than mailchimp
    osf_mailing_lists = DateTimeAwareJSONField(default=get_default_mailing_lists, blank=True)
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # the date this user was registered
    date_registered = NonNaiveDateTimeField(db_index=True, auto_now_add=True)

    # list of collaborators that this user recently added to nodes as a contributor
    # recently_added = fields.ForeignField("user", list=True)
    recently_added = models.ManyToManyField('self',
                                            through=RecentlyAddedContributor,
                                            through_fields=('user', 'contributor'),
                                            symmetrical=False)

    # Attached external accounts (OAuth)
    # external_accounts = fields.ForeignField("externalaccount", list=True)
    external_accounts = models.ManyToManyField('ExternalAccount', blank=True)

    # CSL names
    given_name = models.CharField(max_length=255, blank=True)
    middle_names = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    suffix = models.CharField(max_length=255, blank=True)

    # identity for user logged in through external idp
    external_identity = DateTimeAwareJSONField(default=dict, blank=True)
    # Format: {
    #   <external_id_provider>: {
    #       <external_id>: <status from ('VERIFIED, 'CREATE', 'LINK')>,
    #       ...
    #   },
    #   ...
    # }

    # Employment history
    jobs = DateTimeAwareJSONField(default=list, blank=True, validators=[validate_history_item])
    # Format: list of {
    #     'title': <position or job title>,
    #     'institution': <institution or organization>,
    #     'department': <department>,
    #     'location': <location>,
    #     'startMonth': <start month>,
    #     'startYear': <start year>,
    #     'endMonth': <end month>,
    #     'endYear': <end year>,
    #     'ongoing: <boolean>
    # }

    # Educational history
    schools = DateTimeAwareJSONField(default=list, blank=True, validators=[validate_history_item])
    # Format: list of {
    #     'degree': <position or job title>,
    #     'institution': <institution or organization>,
    #     'department': <department>,
    #     'location': <location>,
    #     'startMonth': <start month>,
    #     'startYear': <start year>,
    #     'endMonth': <end month>,
    #     'endYear': <end year>,
    #     'ongoing: <boolean>
    # }

    # Social links
    social = DateTimeAwareJSONField(default=dict, blank=True, validators=[validate_social])
    # Format: {
    #     'profileWebsites': <list of profile websites>
    #     'twitter': <list of twitter usernames>,
    #     'github': <list of github usernames>,
    #     'linkedIn': <list of linkedin profiles>,
    #     'orcid': <orcid for user>,
    #     'researcherID': <researcherID>,
    #     'impactStory': <impactStory identifier>,
    #     'scholar': <google scholar identifier>,
    #     'ssrn': <SSRN username>,
    #     'researchGate': <researchGate username>,
    #     'baiduScholar': <bauduScholar username>,
    #     'academiaProfileID': <profile identifier for academia.edu>
    # }

    # date the user last sent a request
    date_last_login = NonNaiveDateTimeField(null=True, blank=True, db_index=True)

    # date the user first successfully confirmed an email address
    date_confirmed = NonNaiveDateTimeField(db_index=True, null=True, blank=True)

    # When the user was disabled.
    date_disabled = NonNaiveDateTimeField(db_index=True, null=True, blank=True)

    # When the user was soft-deleted (GDPR)
    deleted = NonNaiveDateTimeField(db_index=True, null=True, blank=True)

    # when comments were last viewed
    comments_viewed_timestamp = DateTimeAwareJSONField(default=dict, blank=True)
    # Format: {
    #   'Comment.root_target._id': 'timestamp',
    #   ...
    # }

    # timezone for user's locale (e.g. 'America/New_York')
    timezone = models.CharField(blank=True, default='Etc/UTC', max_length=255)

    # user language and locale data (e.g. 'en_US')
    locale = models.CharField(blank=True, max_length=255, default='en_US')

    # whether the user has requested to deactivate their account
    requested_deactivation = models.BooleanField(default=False)

    # whether the user has who requested deactivation has been contacted about their pending request. This is reset when
    # requests are canceled
    contacted_deactivation = models.BooleanField(default=False)

    notifications_configured = DateTimeAwareJSONField(default=dict, blank=True)

    # The time at which the user agreed to our updated ToS and Privacy Policy (GDPR, 25 May 2018)
    accepted_terms_of_service = NonNaiveDateTimeField(null=True, blank=True)

    chronos_user_id = models.TextField(null=True, blank=True, db_index=True)

    allow_indexing = models.BooleanField(null=True, blank=True, default=None)

    objects = OSFUserManager()

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    def __repr__(self):
        return f'<OSFUser({self.username!r}) with guid {self._id!r}>'

    @property
    def deep_url(self):
        """Used for GUID resolution."""
        return f'/profile/{self._primary_key}/'

    @property
    def url(self):
        return f'/{self._id}/'

    @property
    def absolute_url(self):
        return urljoin(website_settings.DOMAIN, self.url)

    @property
    def absolute_api_v2_url(self):
        from website import util
        return util.api_v2_url(f'users/{self._id}/')

    @property
    def api_url(self):
        return f'/api/v1/profile/{self._id}/'

    @property
    def profile_url(self):
        return f'/{self._id}/'

    @property
    def is_disabled(self):
        return self.date_disabled is not None

    @is_disabled.setter
    def is_disabled(self, val):
        """Set whether or not this account has been disabled."""
        if val and not self.date_disabled:
            self.date_disabled = timezone.now()
        elif val is False:
            self.date_disabled = None

    @property
    def is_confirmed(self):
        return bool(self.date_confirmed)

    @property
    def is_merged(self):
        """Whether or not this account has been merged into another account.
        """
        return self.merged_by is not None

    @property
    def is_public(self):
        return self.is_active and self.allow_indexing is not False

    @property
    def unconfirmed_emails(self):
        # Handle when email_verifications field is None
        email_verifications = self.email_verifications or {}
        return [
            each['email']
            for each
            in email_verifications.values()
        ]

    @property
    def social_links(self):
        """
        Returns a dictionary of formatted social links for a user.

        Social account values which are stored as account names are
        formatted into appropriate social links. The 'type' of each
        respective social field value is dictated by self.SOCIAL_FIELDS.

        I.e. If a string is expected for a specific social field that
        permits multiple accounts, a single account url will be provided for
        the social field to ensure adherence with self.SOCIAL_FIELDS.
        """
        social_user_fields = {}
        for key, val in self.social.items():
            if val and key in self.SOCIAL_FIELDS:
                if isinstance(self.SOCIAL_FIELDS[key], str):
                    if isinstance(val, str):
                        social_user_fields[key] = self.SOCIAL_FIELDS[key].format(val)
                    else:
                        # Only provide the first url for services where multiple accounts are allowed
                        social_user_fields[key] = self.SOCIAL_FIELDS[key].format(val[0])
                else:
                    if isinstance(val, str):
                        social_user_fields[key] = [val]
                    else:
                        social_user_fields[key] = val
        return social_user_fields

    @property
    def given_name_initial(self):
        """
        The user's preferred initialization of their given name.

        Some users with common names may choose to distinguish themselves from
        their colleagues in this way. For instance, there could be two
        well-known researchers in a single field named "Robert Walker".
        "Walker, R" could then refer to either of them. "Walker, R.H." could
        provide easy disambiguation.

        NOTE: The internal representation for this should never end with a
              period. "R" and "R.H" would be correct in the prior case, but
              "R.H." would not.
        """
        return self.given_name[0]

    @property
    def email(self):
        if self.has_usable_username():
            return self.username
        else:
            return None

    @property
    def all_tags(self):
        """Return a queryset containing all of this user's tags (incl. system tags)."""
        # Tag's default manager only returns non-system tags, so we can't use self.tags
        return Tag.all_tags.filter(osfuser=self)

    @property
    def system_tags(self):
        """The system tags associated with this node. This currently returns a list of string
        names for the tags, for compatibility with v1. Eventually, we can just return the
        QuerySet.
        """
        return self.all_tags.filter(system=True).values_list('name', flat=True)

    @property
    def csl_given_name(self):
        return utils.generate_csl_given_name(self.given_name, self.middle_names, self.suffix)

    def csl_name(self, node_id=None):
        # disabled users are set to is_registered = False but have a fullname
        if self.is_registered or self.is_disabled:
            name = self.fullname
        else:
            name = self.get_unclaimed_record(node_id)['name']

        # Unregistered contributors' names may vary across unclaimed records
        if self.is_registered and self.family_name and self.given_name:
            """If a registered user has a family and given name, use those"""
            return {
                'family': self.family_name,
                'given': self.csl_given_name,
            }
        else:
            """ If the user is unregistered or doesn't autofill his family and given name """
            parsed = utils.impute_names(name)
            given_name = parsed['given']
            middle_names = parsed['middle']
            family_name = parsed['family']
            suffix = parsed['suffix']
            csl_given_name = utils.generate_csl_given_name(given_name, middle_names, suffix)
            return {
                'family': family_name,
                'given': csl_given_name,
            }

    @property
    def osfstorage_region(self):
        from addons.osfstorage.models import Region
        osfs_settings = self._settings_model('osfstorage')
        region_subquery = osfs_settings.objects.get(owner=self.id).default_region_id
        return Region.objects.get(id=region_subquery)

    @property
    def contributor_to(self):
        """
        Nodes that user has perms to through contributorship - group membership not factored in
        """
        return self.nodes.filter(is_deleted=False, type__in=['osf.node', 'osf.registration'])

    @property
    def visible_contributor_to(self):
        """
        Nodes where user is a bibliographic contributor (group membership not factored in)
        """
        return self.nodes.annotate(
            self_is_visible=Exists(Contributor.objects.filter(node_id=OuterRef('id'), user_id=self.id, visible=True))
        ).filter(deleted__isnull=True, self_is_visible=True, type__in=['osf.node', 'osf.registration'])

    @property
    def all_nodes(self):
        """
        Return all AbstractNodes that the user has explicit permissions to - either through contributorship or group membership
        - similar to guardian.get_objects_for_user(self, READ_NODE, AbstractNode, with_superuser=False), but not looking at
        NodeUserObjectPermissions, just NodeGroupObjectPermissions.
        """
        from osf.models import AbstractNode
        return AbstractNode.objects.get_nodes_for_user(self)

    @property
    def contributor_or_group_member_to(self):
        """
        Nodes and registrations that user has perms to through contributorship or group membership
        """
        return self.all_nodes.filter(type__in=['osf.node', 'osf.registration'])

    @property
    def nodes_contributor_or_group_member_to(self):
        """
        Nodes that user has perms to through contributorship or group membership
        """
        from osf.models import Node
        return Node.objects.get_nodes_for_user(self)

    def set_unusable_username(self):
        """Sets username to an unusable value. Used for, e.g. for invited contributors
        and merged users.

        NOTE: This is necessary because Django does not allow the username column to be nullable.
        """
        if self._id:
            self.username = self._id
        else:
            self.username = str(uuid.uuid4())
        return self.username

    def has_usable_username(self):
        return '@' in self.username

    @property
    def is_authenticated(self):  # Needed for django compat
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def osf_groups(self):
        """
        OSFGroups that the user belongs to
        """
        OSFGroup = apps.get_model('osf.OSFGroup')
        return get_objects_for_user(self, 'member_group', OSFGroup, with_superuser=False)

    def is_institutional_admin_at(self, institution):
        """
        Checks if user is admin of a specific institution.
        """
        return self.has_perms(
            institution.groups['institutional_admins'],
            institution
        )

    def is_institutional_admin(self):
        """
        Checks if user is admin of any institution.
        """
        return self.groups.filter(
            name__startswith='institution_',
            name__endswith='_institutional_admins'
        ).exists()

    def is_institutional_curator(self, node):
        """
        Checks if user is user has curator permissions for a node.
        """
        return Contributor.objects.filter(
            node=node,
            user=self,
            is_curator=True,
        ).exists()

    def group_role(self, group):
        """
        For the given OSFGroup, return the user's role - either member or manager
        """
        if group.is_manager(self):
            return MANAGER
        elif group.is_member(self):
            return MEMBER
        else:
            return None

    def has_groups(self, groups):
        """
        Checks if user is a member of the group(s).
        """
        return self.groups.filter(name__in=groups).exists()

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def get_addon_names(self):
        return []

    # django methods
    def get_full_name(self):
        return self.fullname

    def get_short_name(self):
        return self.username

    def __unicode__(self):
        return self.get_short_name()

    def __str__(self):
        return self.get_short_name()

    def get_verified_external_id(self, external_service, verified_only=False):
        identifier_info = self.external_identity.get(external_service, {})
        for external_id, status in identifier_info.items():
            if status and status == 'VERIFIED' or not verified_only:
                return external_id
        return None

    @property
    def contributed(self):
        return self.nodes.all()

    def merge_user(self, user):
        """Merge a registered user into this account. This user will be
        a contributor on any project. if the registered user and this account
        are both contributors of the same project. Then it will remove the
        registered user and set this account to the highest permission of the two
        and set this account to be visible if either of the two are visible on
        the project.

        :param user: A User object to be merged.
        """

        # Attempt to prevent self merges which end up removing self as a contributor from all projects
        if self == user:
            raise ValueError('Cannot merge a user into itself')

        # Move over the other user's attributes
        # TODO: confirm
        for system_tag in user.system_tags.all():
            self.add_system_tag(system_tag)

        self.is_registered = self.is_registered or user.is_registered
        self.is_invited = self.is_invited or user.is_invited
        self.is_superuser = self.is_superuser or user.is_superuser
        self.is_staff = self.is_staff or user.is_staff

        # copy over profile only if this user has no profile info
        if user.jobs and not self.jobs:
            self.jobs = user.jobs

        if user.schools and not self.schools:
            self.schools = user.schools

        if user.social and not self.social:
            self.social = user.social

        unclaimed = user.unclaimed_records.copy()
        unclaimed.update(self.unclaimed_records)
        self.unclaimed_records = unclaimed
        # - unclaimed records should be connected to only one user
        user.unclaimed_records = {}

        security_messages = user.security_messages.copy()
        security_messages.update(self.security_messages)
        self.security_messages = security_messages

        notifications_configured = user.notifications_configured.copy()
        notifications_configured.update(self.notifications_configured)
        self.notifications_configured = notifications_configured
        for target_id, timestamp in user.comments_viewed_timestamp.items():
            if not self.comments_viewed_timestamp.get(target_id):
                self.comments_viewed_timestamp[target_id] = timestamp
            elif timestamp > self.comments_viewed_timestamp[target_id]:
                self.comments_viewed_timestamp[target_id] = timestamp

        # Give old user's emails to self
        user.emails.update(user=self)

        for k, v in user.email_verifications.items():
            email_to_confirm = v['email']
            if k not in self.email_verifications and email_to_confirm != user.username:
                self.email_verifications[k] = v
        user.email_verifications = {}

        self.copy_institution_affiliation_when_merging_user(user)
        # Institution affiliations must be removed from the merged user to avoid duplicate identity during SSO
        user.remove_all_affiliated_institutions()

        for service in user.external_identity:
            for service_id in user.external_identity[service].keys():
                if not (
                    service_id in self.external_identity.get(service, '') and
                    self.external_identity[service][service_id] == 'VERIFIED'
                ):
                    # Prevent 'CREATE', merging user has already been created.
                    external = user.external_identity[service][service_id]
                    status = 'VERIFIED' if external == 'VERIFIED' else 'LINK'
                    if self.external_identity.get(service):
                        self.external_identity[service].update(
                            {service_id: status}
                        )
                    else:
                        self.external_identity[service] = {
                            service_id: status
                        }
        user.external_identity = {}

        # FOREIGN FIELDS
        self.external_accounts.add(*user.external_accounts.values_list('pk', flat=True))

        # - projects where the user was a contributor (group member only are not included).
        for node in user.contributed:
            # Skip quickfiles
            if node.is_quickfiles:
                continue
            user_perms = Contributor(node=node, user=user).permission
            # if both accounts are contributor of the same project
            if node.is_contributor(self) and node.is_contributor(user):
                self_perms = Contributor(node=node, user=self).permission
                permissions = API_CONTRIBUTOR_PERMISSIONS[max(API_CONTRIBUTOR_PERMISSIONS.index(user_perms), API_CONTRIBUTOR_PERMISSIONS.index(self_perms))]
                node.set_permissions(user=self, permissions=permissions)

                visible1 = self._id in node.visible_contributor_ids
                visible2 = user._id in node.visible_contributor_ids
                if visible1 != visible2:
                    node.set_visible(user=self, visible=True, log=True, auth=Auth(user=self))

                node.contributor_set.filter(user=user).delete()
            else:
                node.contributor_set.filter(user=user).update(user=self)
                node.add_permission(self, user_perms)

            node.remove_permission(user, user_perms)
            node.save()

        # Skip bookmark collections
        user.collection_set.exclude(is_bookmark_collection=True).update(creator=self)

        from .files import BaseFileNode
        from .quickfiles import QuickFilesNode

        # - projects where the user was the creator
        user.nodes_created.exclude(type=QuickFilesNode._typedmodels_type).update(creator=self)

        # - file that the user has checked_out, import done here to prevent import error
        for file_node in BaseFileNode.files_checked_out(user=user):
            file_node.checkout = self
            file_node.save()

        # Transfer user's preprints
        self._merge_users_preprints(user)

        # Transfer user's draft registrations
        self._merge_user_draft_registrations(user)

        # transfer group membership
        for group in user.osf_groups:
            if not group.is_manager(self):
                if group.has_permission(user, MANAGE):
                    group.make_manager(self)
                else:
                    group.make_member(self)
            group.remove_member(user)

        # finalize the merge

        remove_sessions_for_user(user)

        # - username is set to the GUID so the merging user can set it primary
        #   in the future (note: it cannot be set to None due to non-null constraint)
        user.set_unusable_username()
        user.set_unusable_password()
        user.verification_key = None
        user.osf_mailing_lists = {}
        user.merged_by = self

        user.save()
        signals.user_account_merged.send(user)

    def _merge_users_preprints(self, user):
        """
        Preprints use guardian.  The PreprintContributor table stores order and bibliographic information.
        Permissions are stored on guardian tables.  PreprintContributor information needs to be transferred
        from user -> self, and preprint permissions need to be transferred from user -> self.
        """
        from .preprint import PreprintContributor

        # Loop through `user`'s preprints
        for preprint in user.preprints.all():
            user_contributor = PreprintContributor.objects.get(preprint=preprint, user=user)
            user_perms = user_contributor.permission

            # Both `self` and `user` are contributors on the preprint
            if preprint.is_contributor(self) and preprint.is_contributor(user):
                self_contributor = PreprintContributor.objects.get(preprint=preprint, user=self)
                self_perms = self_contributor.permission

                max_perms_index = max(API_CONTRIBUTOR_PERMISSIONS.index(self_perms), API_CONTRIBUTOR_PERMISSIONS.index(user_perms))
                # Add the highest of `self` perms or `user` perms to `self`
                preprint.set_permissions(user=self, permissions=API_CONTRIBUTOR_PERMISSIONS[max_perms_index])

                if not self_contributor.visible and user_contributor.visible:
                    # if `self` is not visible, but `user` is visible, make `self` visible.
                    preprint.set_visible(user=self, visible=True, log=True, auth=Auth(user=self))
                # Now that perms and bibliographic info have been transferred to `self` contributor,
                # delete `user` contributor
                user_contributor.delete()
            else:
                # `self` is not a contributor, but `user` is.  Transfer `user` permissions and
                # contributor information to `self`.  Remove permissions from `user`.
                preprint.contributor_set.filter(user=user).update(user=self)
                preprint.add_permission(self, user_perms)

            if preprint.creator == user:
                preprint.creator = self

            preprint.remove_permission(user, user_perms)
            preprint.save()

    @property
    def draft_registrations_active(self):
        """
        Active draft registrations attached to a user (user is a contributor)
        """

        return self.draft_registrations.filter(
            (models.Q(registered_node__isnull=True) | models.Q(registered_node__deleted__isnull=False)),
            branched_from__deleted__isnull=True,
            deleted__isnull=True,
        )

    def _merge_user_draft_registrations(self, user):
        """
        Draft Registrations have contributors, and this model uses guardian.
        The DraftRegistrationContributor table stores order and bibliographic information.
        Permissions are stored on guardian tables.  DraftRegistration information needs to be transferred
        from user -> self, and draft registration permissions need to be transferred from user -> self.
        """
        from osf.models import DraftRegistrationContributor
        # Loop through `user`'s draft registrations
        for draft_reg in user.draft_registrations.all():
            user_contributor = DraftRegistrationContributor.objects.get(draft_registration=draft_reg, user=user)
            user_perms = user_contributor.permission

            # Both `self` and `user` are contributors on the draft reg
            if draft_reg.is_contributor(self) and draft_reg.is_contributor(user):
                self_contributor = DraftRegistrationContributor.objects.get(draft_registration=draft_reg, user=self)
                self_perms = self_contributor.permission

                max_perms_index = max(API_CONTRIBUTOR_PERMISSIONS.index(self_perms), API_CONTRIBUTOR_PERMISSIONS.index(user_perms))
                # Add the highest of `self` perms or `user` perms to `self`
                draft_reg.set_permissions(user=self, permissions=API_CONTRIBUTOR_PERMISSIONS[max_perms_index])

                if not self_contributor.visible and user_contributor.visible:
                    # if `self` is not visible, but `user` is visible, make `self` visible.
                    draft_reg.set_visible(user=self, visible=True, log=True, auth=Auth(user=self))
                # Now that perms and bibliographic info have been transferred to `self` contributor,
                # delete `user` contributor
                user_contributor.delete()
            else:
                # `self` is not a contributor, but `user` is.  Transfer `user` permissions and
                # contributor information to `self`.  Remove permissions from `user`.
                draft_reg.contributor_set.filter(user=user).update(user=self)
                draft_reg.add_permission(self, user_perms)

            if draft_reg.initiator == user:
                draft_reg.initiator = self

            draft_reg.remove_permission(user, user_perms)
            draft_reg.save()

    def deactivate_account(self):
        """
        Disables user account, making is_disabled true, while also unsubscribing user
        from mailchimp emails, remove any existing sessions.

        Ported from framework/auth/core.py
        """
        from website import mailchimp_utils
        from framework.auth import logout

        try:
            mailchimp_utils.unsubscribe_mailchimp(
                list_name=website_settings.MAILCHIMP_GENERAL_LIST,
                user_id=self._id,
                username=self.username
            )
        except mailchimp_utils.OSFError as error:
            sentry.log_exception(error)
        except Exception as error:
            sentry.log_exception(error)
        # Call to `unsubscribe` above saves, and can lead to stale data
        self.reload()
        self.is_disabled = True
        signals.user_account_deactivated.send(self)

        # we must call both methods to ensure the current session is cleared and all existing
        # sessions are revoked.
        req = get_current_request()
        if isinstance(req, FlaskRequest):
            logout()
        remove_sessions_for_user(self)

    def reactivate_account(self):
        """
        Enable user account
        """
        self.is_disabled = False
        self.requested_deactivation = False
        from website.mailchimp_utils import subscribe_on_confirm, OSFError
        try:
            subscribe_on_confirm(self)
        except OSFError as error:
            sentry.log_exception(error)
        except Exception as error:
            sentry.log_exception(error)
        signals.user_account_reactivated.send(self)

    def update_is_active(self):
        """Update ``is_active`` to be consistent with the fields that
        it depends on.
        """
        # The user can log in if they have set a password OR
        # have a verified external ID, e.g an ORCID
        can_login = self.has_usable_password() or (
            'VERIFIED' in sum([list(each.values()) for each in self.external_identity.values()], [])
        )
        self.is_active = (
            self.is_registered and
            self.is_confirmed and
            can_login and
            not self.is_merged and
            not self.is_disabled
        )

    # Overrides BaseModel
    def save(self, *args, **kwargs):
        from website import mailchimp_utils

        self.update_is_active()
        self.username = self.username.lower().strip() if self.username else None

        dirty_fields = self.get_dirty_fields(check_relationship=True)
        ret = super().save(*args, **kwargs)  # must save BEFORE spam check, as user needs guid.
        if set(self.SPAM_USER_PROFILE_FIELDS.keys()).intersection(dirty_fields):
            request = get_current_request()
            headers = get_headers_from_request(request)
            self.check_spam(dirty_fields, request_headers=headers)

        dirty_fields = set(dirty_fields)
        if self.SEARCH_UPDATE_FIELDS.intersection(dirty_fields) and self.is_confirmed:
            self.update_search()
            self.update_search_nodes_contributors()
        if 'fullname' in dirty_fields:
            from .quickfiles import get_quickfiles_project_title, QuickFilesNode

            quickfiles = QuickFilesNode.objects.filter(creator=self).first()
            if quickfiles:
                quickfiles.title = get_quickfiles_project_title(self)
                quickfiles.save()
        if 'username' in dirty_fields:
            for list_name, subscription in self.mailchimp_mailing_lists.items():
                if subscription:
                    mailchimp_utils.subscribe_mailchimp(list_name, self._id)
        return ret

    # Legacy methods

    @classmethod
    def create(cls, username, password, fullname, accepted_terms_of_service=None):
        validate_email(username)  # Raises BlockedEmailError if spam address

        user = cls(
            username=username,
            fullname=fullname,
            accepted_terms_of_service=accepted_terms_of_service
        )
        user.update_guessed_names()
        user.set_password(password)
        user.save()
        return user

    def set_password(self, raw_password, notify=True):
        """Set the password for this user to the hash of ``raw_password``.
        If this is a new user, we're done. If this is a password change,
        then email the user about the change and clear all the old sessions
        so that users will have to log in again with the new password.

        :param raw_password: the plaintext value of the new password
        :param notify: Only meant for unit tests to keep extra notifications from being sent
        :rtype: list
        :returns: Changed fields from the user save
        """
        had_existing_password = bool(self.has_usable_password() and self.is_confirmed)
        if self.username == raw_password:
            raise ChangePasswordError(['Password cannot be the same as your email address'])
        super().set_password(raw_password)
        if had_existing_password and notify:
            mails.send_mail(
                to_addr=self.username,
                mail=mails.PASSWORD_RESET,
                user=self,
                can_change_preferences=False,
                osf_contact_email=website_settings.OSF_CONTACT_EMAIL
            )
            remove_sessions_for_user(self)

    @classmethod
    def create_unconfirmed(cls, username, password, fullname, external_identity=None,
                           do_confirm=True, campaign=None, accepted_terms_of_service=None):
        """Create a new user who has begun registration but needs to verify
        their primary email address (username).
        """
        user = cls.create(username, password, fullname, accepted_terms_of_service)
        user.add_unconfirmed_email(username, external_identity=external_identity)
        user.is_registered = False
        if external_identity:
            user.external_identity.update(external_identity)
        if campaign:
            # needed to prevent cirular import
            from framework.auth.campaigns import system_tag_for_campaign  # skipci
            # User needs to be saved before adding system tags (due to m2m relationship)
            user.save()
            user.add_system_tag(system_tag_for_campaign(campaign))
        else:
            user.save()
            user.add_system_tag(OsfSourceTags.Osf.value)
        return user

    @classmethod
    def create_confirmed(cls, username, password, fullname):
        user = cls.create(username, password, fullname)
        user.is_registered = True
        user.save()  # Must save before using auto_now_add field
        user.date_confirmed = user.date_registered
        user.emails.create(address=username.lower().strip())
        return user

    def get_unconfirmed_email_for_token(self, token):
        """Return email if valid.
        :rtype: bool
        :raises: ExpiredTokenError if trying to access a token that is expired.
        :raises: InvalidTokenError if trying to access a token that is invalid.

        """
        if token not in self.email_verifications:
            raise InvalidTokenError

        verification = self.email_verifications[token]
        # Not all tokens are guaranteed to have expiration dates
        if (
            'expiration' in verification and
            verification['expiration'].replace(tzinfo=pytz.utc) < timezone.now()
        ):
            raise ExpiredTokenError

        return verification['email']

    def get_unconfirmed_emails_exclude_external_identity(self):
        """Return a list of unconfirmed emails that are not related to external identity."""

        unconfirmed_emails = []
        if self.email_verifications:
            for token, value in self.email_verifications.items():
                if not value.get('external_identity'):
                    unconfirmed_emails.append(value.get('email'))
        return unconfirmed_emails

    @property
    def unconfirmed_email_info(self):
        """Return a list of dictionaries containing information about each of this
        user's unconfirmed emails.
        """
        unconfirmed_emails = []
        email_verifications = self.email_verifications or []
        for token in email_verifications:
            if self.email_verifications[token].get('confirmed', False):
                try:
                    user_merge = OSFUser.objects.get(emails__address__iexact=self.email_verifications[token]['email'])
                except OSFUser.DoesNotExist:
                    user_merge = False

                unconfirmed_emails.append({'address': self.email_verifications[token]['email'],
                                        'token': token,
                                        'confirmed': self.email_verifications[token]['confirmed'],
                                        'user_merge': user_merge.email if user_merge else False})
        return unconfirmed_emails

    def clean_email_verifications(self, given_token=None):
        email_verifications = deepcopy(self.email_verifications or {})
        for token in self.email_verifications or {}:
            try:
                self.get_unconfirmed_email_for_token(token)
            except (KeyError, ExpiredTokenError):
                email_verifications.pop(token)
                continue
            if token == given_token:
                email_verifications.pop(token)
        self.email_verifications = email_verifications

    def verify_password_token(self, token):
        """
        Verify that the password reset token for this user is valid.

        :param token: the token in verification key
        :return `True` if valid, otherwise `False`
        """

        if token and self.verification_key_v2:
            try:
                return (self.verification_key_v2['token'] == token and
                        self.verification_key_v2['expires'] > timezone.now())
            except AttributeError:
                return False
        return False

    def verify_claim_token(self, token, project_id):
        """Return whether or not a claim token is valid for this user for
        a given node which they were added as a unregistered contributor for.
        """
        try:
            record = self.get_unclaimed_record(project_id)
        except ValueError:  # No unclaimed record for given pid
            return False
        return record['token'] == token

    @classmethod
    def create_unregistered(cls, fullname, email=None):
        """Create a new unregistered user.
        """
        user = cls(
            username=email,
            fullname=fullname,
            is_invited=True,
            is_registered=False,
        )
        if not email:
            user.set_unusable_username()
        user.set_unusable_password()
        user.update_guessed_names()

        return user

    def update_guessed_names(self):
        """Updates the CSL name fields inferred from the the full name.
        """
        parsed = impute_names(self.fullname)
        self.given_name = parsed['given']
        self.middle_names = parsed['middle']
        self.family_name = parsed['family']
        self.suffix = parsed['suffix']

    def add_unconfirmed_email(self, email, expiration=None, external_identity=None, force=False):
        """
        Add an email verification token for a given email.

        :param email: the email to confirm
        :param expiration: overwrite default expiration time
        :param external_identity: the user's external identity
        :return: a token
        :raises: ValueError if email already confirmed, except for login through external idp.
        """

        # Note: This is technically not compliant with RFC 822, which requires
        #       that case be preserved in the "local-part" of an address. From
        #       a practical standpoint, the vast majority of email servers do
        #       not preserve case.
        #       ref: https://tools.ietf.org/html/rfc822#section-6
        email = email.lower().strip()

        with reraise_django_validation_errors():
            validate_email(email)

        if not external_identity and self.emails.filter(address=email).exists():
            if not force and self.is_confirmed:
                raise ValueError('Email already confirmed to this user.')

        # If the unconfirmed email is already present, refresh the token
        if email in self.unconfirmed_emails:
            self.remove_unconfirmed_email(email)

        verification_key = generate_verification_key(verification_type='confirm')

        # handle when email_verifications is None
        if not self.email_verifications:
            self.email_verifications = {}

        self.email_verifications[verification_key['token']] = {
            'email': email,
            'confirmed': False,
            'expiration': expiration if expiration else verification_key['expires'],
            'external_identity': external_identity,
        }

        return verification_key['token']

    def remove_unconfirmed_email(self, email):
        """Remove an unconfirmed email addresses and their tokens."""
        for token, value in self.email_verifications.items():
            if value.get('email') == email:
                del self.email_verifications[token]
                return True

        return False

    def remove_email(self, email):
        """Remove a confirmed email"""
        if email == self.username:
            raise PermissionsError("Can't remove primary email")
        if self.emails.filter(address=email):
            self.emails.filter(address=email).delete()
            signals.user_email_removed.send(self, email=email, osf_contact_email=website_settings.OSF_CONTACT_EMAIL)

    def get_confirmation_token(self, email, force=False, renew=False):
        """Return the confirmation token for a given email.

        :param str email: The email to get the token for.
        :param bool force: If an expired token exists for the given email, generate a new one and return it.
        :param bool renew: Generate a new token and return it.
        :return Return the confirmation token.
        :raises: ExpiredTokenError if trying to access a token that is expired and force=False.
        :raises: KeyError if there no token for the email.
        """
        # TODO: Refactor "force" flag into User.get_or_add_confirmation_token
        for token, info in self.email_verifications.items():
            if info['email'].lower() == email.lower():
                # Old records will not have an expiration key. If it's missing,
                # assume the token is expired
                expiration = info.get('expiration')
                if renew:
                    new_token = self.add_unconfirmed_email(email, force=force)
                    self.save()
                    return new_token
                if not expiration or (expiration and expiration < timezone.now()):
                    if not force:
                        raise ExpiredTokenError(f'Token for email "{email}" is expired')
                    else:
                        new_token = self.add_unconfirmed_email(email, force=force)
                        self.save()
                        return new_token
                return token
        raise KeyError(f'No confirmation token for email "{email}"')

    def get_confirmation_url(self, email,
                             external=True,
                             force=False,
                             renew=False,
                             external_id_provider=None,
                             destination=None):
        """Return the confirmation url for a given email.

        :param email: The email to confirm.
        :param external: Use absolute or relative url.
        :param force: If an expired token exists for the given email, generate a new one and return it.
        :param renew: Generate a new token and return it.
        :param external_id_provider: The external identity provider that authenticates the user.
        :param destination: The destination page to redirect after confirmation
        :return: Return the confirmation url.
        :raises: ExpiredTokenError if trying to access a token that is expired.
        :raises: KeyError if there is no token for the email.
        """

        base = website_settings.DOMAIN if external else '/'
        token = self.get_confirmation_token(email, force=force, renew=renew)
        external = 'external/' if external_id_provider else ''
        destination = '?{}'.format(urlencode({'destination': destination})) if destination else ''
        return f'{base}confirm/{external}{self._primary_key}/{token}/{destination}'

    def get_or_create_confirmation_url(self, email, force=False, renew=False):
        """
        Get or create a confirmation URL for the given email.

        :param email: The email to generate a confirmation URL for.
        :param force: Force generating a new confirmation link.
        :param renew: Renew an expired token.
        :raises ValidationError: If email is invalid or domain is banned.
        :return: Confirmation URL for the email.
        """
        try:
            self.get_confirmation_token(email, force=force, renew=renew)
        except KeyError:
            self.add_unconfirmed_email(email, force=force)
            self.save()
        return self.get_confirmation_url(email)

    def register(self, username, password=None, accepted_terms_of_service=None):
        """Registers the user.
        """
        self.username = username
        if password:
            self.set_password(password)
        if not self.emails.filter(address=username):
            self.emails.create(address=username)
        self.is_registered = True
        self.date_confirmed = timezone.now()
        if accepted_terms_of_service:
            self.accepted_terms_of_service = timezone.now()
        self.update_search()
        self.update_search_nodes()

        # Emit signal that a user has confirmed
        signals.user_confirmed.send(self)

        return self

    def confirm_email(self, token, merge=False):
        """Confirm the email address associated with the token"""
        email = self.get_unconfirmed_email_for_token(token)

        # If this email is confirmed on another account, abort
        try:
            if check_select_for_update():
                user_to_merge = OSFUser.objects.exclude(id=self.id).filter(emails__address=email).select_for_update().get()
            else:
                user_to_merge = OSFUser.objects.exclude(id=self.id).get(emails__address=email)
        except OSFUser.DoesNotExist:
            user_to_merge = None

        if user_to_merge and merge:
            self.merge_user(user_to_merge)
        elif user_to_merge:
            raise MergeConfirmedRequiredError(
                'Merge requires confirmation',
                user=self,
                user_to_merge=user_to_merge,
            )

        # If another user has this email as its username, get it
        try:
            unregistered_user = OSFUser.objects.exclude(guids___id=self._id, guids___id__isnull=False).get(username=email)
        except OSFUser.DoesNotExist:
            unregistered_user = None

        if unregistered_user:
            self.merge_user(unregistered_user)
            self.save()
            unregistered_user.username = None

        if not self.emails.filter(address=email).exists():
            self.emails.create(address=email)

        # Complete registration if primary email
        if email.lower() == self.username.lower():
            self.register(self.username)
            self.date_confirmed = timezone.now()
        # Revoke token
        del self.email_verifications[token]

        # TODO: We can't assume that all unclaimed records are now claimed.
        # Clear unclaimed records, so user's name shows up correctly on
        # all projects
        self.unclaimed_records = {}
        self.save()

        self.update_search_nodes()

        return True

    def confirm_spam(self, domains=None, save=True, train_spam_services=False):
        self.deactivate_account()
        super().confirm_spam(domains=domains, save=save, train_spam_services=train_spam_services)

        # Don't train on resources merely associated with spam user
        for node in self.nodes.filter(is_public=True, is_deleted=False).exclude(type='osf.quickfilesnode'):
            node.confirm_spam(train_spam_services=train_spam_services)
        for preprint in self.preprints.filter(is_public=True, deleted__isnull=True):
            preprint.confirm_spam(train_spam_services=train_spam_services)

    def confirm_ham(self, save=False, train_spam_services=False):
        self.reactivate_account()
        super().confirm_ham(save=save, train_spam_services=train_spam_services)

        # Don't train on resources merely associated with spam user
        for node in self.nodes.filter().exclude(type='osf.quickfilesnode'):
            node.confirm_ham(save=save, train_spam_services=train_spam_services)
        for preprint in self.preprints.filter():
            preprint.confirm_ham(save=save, train_spam_services=train_spam_services)

    @property
    def is_assumed_ham(self):
        user_email_addresses = self.emails.values_list('address', flat=True)
        user_email_domains = [
            # get everything after the @
            address.rpartition('@')[2].lower()
            for address in user_email_addresses
        ]
        user_has_trusted_email = NotableDomain.objects.filter(
            note=NotableDomain.Note.ASSUME_HAM_UNTIL_REPORTED,
            domain__in=user_email_domains,
        ).exists()

        return user_has_trusted_email

    def update_search(self):
        from api.share.utils import update_share
        update_share(self)
        from website.search.search import update_user
        update_user(self)

    def update_search_nodes_contributors(self):
        """
        Bulk update contributor name on all nodes on which the user is
        a contributor.
        :return:
        """
        from website.search import search
        search.update_contributors_async(self.id)

    def update_search_nodes(self):
        """Call `update_search` on all nodes on which the user is a
        contributor. Needed to add self to contributor lists in search upon
        registration or claiming.
        """
        # Group member names not listed on Node search result, just Group names, so don't
        # need to update nodes where user has group member perms only
        for node in self.contributor_to:
            node.update_search()

        for group in self.osf_groups:
            group.update_search()

    def update_date_last_login(self, login_time=None):
        self.date_last_login = login_time or timezone.now()

    def get_summary(self, formatter='long'):
        return {
            'user_fullname': self.fullname,
            'user_profile_url': self.profile_url,
            'user_display_name': name_formatters[formatter](self),
            'user_is_registered': self.is_registered
        }

    def check_password(self, raw_password):
        """
        Return a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.

        Source: https://github.com/django/django/blob/master/django/contrib/auth/base_user.py#L104
        """
        def setter(raw_password):
            self.set_password(raw_password, notify=False)
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            self.save(update_fields=['password'])
        return check_password(raw_password, self.password, setter)

    def change_password(self, raw_old_password, raw_new_password, raw_confirm_password):
        """Change the password for this user to the hash of ``raw_new_password``."""
        raw_old_password = (raw_old_password or '').strip()
        raw_new_password = (raw_new_password or '').strip()
        raw_confirm_password = (raw_confirm_password or '').strip()

        # TODO: Move validation to set_password
        issues = []
        if not self.check_password(raw_old_password):
            self.old_password_invalid_attempts += 1
            self.change_password_last_attempt = timezone.now()
            issues.append('Old password is invalid')
        elif raw_old_password == raw_new_password:
            issues.append('Password cannot be the same')
        elif raw_new_password == self.username:
            issues.append('Password cannot be the same as your email address')
        if not raw_old_password or not raw_new_password or not raw_confirm_password:
            issues.append('Passwords cannot be blank')
        elif len(raw_new_password) < 8:
            issues.append('Password should be at least eight characters')
        elif len(raw_new_password) > 256:
            issues.append('Password should not be longer than 256 characters')

        if raw_new_password != raw_confirm_password:
            issues.append('Password does not match the confirmation')

        if issues:
            raise ChangePasswordError(issues)
        self.set_password(raw_new_password)
        self.reset_old_password_invalid_attempts()
        if self.verification_key_v2:
            self.verification_key_v2['expires'] = timezone.now()
        # new verification key (v1) for CAS
        self.verification_key = generate_verification_key(verification_type=None)

    def reset_old_password_invalid_attempts(self):
        self.old_password_invalid_attempts = 0

    def profile_image_url(self, size=None):
        """A generalized method for getting a user's profile picture urls.
        We may choose to use some service other than gravatar in the future,
        and should not commit ourselves to using a specific service (mostly
        an API concern).

        As long as we use gravatar, this is just a proxy to User.gravatar_url
        """
        return self._gravatar_url(size)

    def _gravatar_url(self, size):
        return filters.gravatar(
            self,
            use_ssl=True,
            size=size
        )

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    def display_full_name(self, node=None):
        """Return the full name , as it would display in a contributor list for a
        given node.

        NOTE: Unclaimed users may have a different name for different nodes.
        """
        if node:
            unclaimed_data = self.unclaimed_records.get(str(node._id), None)
            if unclaimed_data:
                return unclaimed_data['name']
        return self.fullname

    def add_system_tag(self, tag):
        if not isinstance(tag, Tag):
            tag_instance, created = Tag.all_tags.get_or_create(name=tag.lower(), system=True)
        else:
            tag_instance = tag
        if not tag_instance.system:
            raise ValueError('Non-system tag passed to add_system_tag')
        if not self.all_tags.filter(id=tag_instance.id).exists():
            self.tags.add(tag_instance)
        return tag_instance

    def get_recently_added(self):
        return (
            each.contributor
            for each in self.recentlyaddedcontributor_set.order_by('-date_added')
        )

    def _projects_in_common_query(self, other_user):
        """
        Returns projects that both self and other_user have in common; both are either contributors or group members
        """
        from osf.models import AbstractNode

        return AbstractNode.objects.get_nodes_for_user(other_user, base_queryset=self.contributor_or_group_member_to).exclude(type='osf.collection')

    def get_projects_in_common(self, other_user):
        """Returns either a collection of "shared projects" (projects that both users are contributors or group members for)
        or just their primary keys
        """
        query = self._projects_in_common_query(other_user)
        return set(query.all())

    def n_projects_in_common(self, other_user):
        """Returns number of "shared projects" (projects that both users are contributors or group members for)"""
        return self._projects_in_common_query(other_user).count()

    def add_unclaimed_record(self, claim_origin, referrer, given_name, email=None, skip_referrer_permissions=False):
        """Add a new project entry in the unclaimed records dictionary.

        :param object claim_origin: Object this unclaimed user was added to. currently `Node` or `Provider` or `Preprint`
        :param User referrer: User who referred this user.
        :param str given_name: The full name that the referrer gave for this user.
        :param str email: The given email address.
        :param bool skip_referrer_permissions: The flag to check permissions for referrer.
        :returns: The added record
        """

        from .provider import AbstractProvider
        from .osf_group import OSFGroup

        if not skip_referrer_permissions:
            if isinstance(claim_origin, AbstractProvider):
                if not bool(get_perms(referrer, claim_origin)):
                    raise PermissionsError(
                        f'Referrer does not have permission to add a moderator to provider {claim_origin._id}'
                    )

            elif isinstance(claim_origin, OSFGroup):
                if not claim_origin.has_permission(referrer, MANAGE):
                    raise PermissionsError(
                        f'Referrer does not have permission to add a member to {claim_origin._id}'
                    )
            else:
                if not claim_origin.has_permission(referrer, ADMIN):
                    raise PermissionsError(
                        f'Referrer does not have permission to add a contributor to {claim_origin._id}'
                    )

        pid = str(claim_origin._id)
        referrer_id = str(referrer._id)
        if email:
            clean_email = email.lower().strip()
        else:
            clean_email = None
        verification_key = generate_verification_key(verification_type='claim')
        try:
            record = self.unclaimed_records[claim_origin._id]
        except KeyError:
            record = None
        if record:
            del record
        record = {
            'name': given_name,
            'referrer_id': referrer_id,
            'token': verification_key['token'],
            'expires': verification_key['expires'],
            'email': clean_email,
        }
        self.unclaimed_records[pid] = record

        self.save()  # must save for PK to add system tags
        self.add_system_tag(unregistered_created_source_tag(referrer_id))

        return record

    def get_unclaimed_record(self, project_id):
        """Get an unclaimed record for a given project_id.

        :raises: ValueError if there is no record for the given project.
        """
        try:
            return self.unclaimed_records[project_id]
        except KeyError:  # reraise as ValueError
            raise ValueError(f'No unclaimed record for user {self._id} on node {project_id}')

    def get_claim_url(self, project_id, external=False):
        """Return the URL that an unclaimed user should use to claim their
        account. Return ``None`` if there is no unclaimed_record for the given
        project ID.

        :param project_id: The project ID/preprint ID/OSF group ID for the unclaimed record
        :raises: ValueError if a record doesn't exist for the given project ID
        :rtype: dict
        :returns: The unclaimed record for the project
        """
        uid = self._primary_key
        base_url = website_settings.DOMAIN if external else '/'
        unclaimed_record = self.get_unclaimed_record(project_id)
        token = unclaimed_record['token']
        return f'{base_url}user/{uid}/{project_id}/claim/?token={token}'

    def is_affiliated_with_institution(self, institution):
        """Return if this user is affiliated with the given ``institution``."""
        if not institution:
            return False
        return InstitutionAffiliation.objects.filter(user__id=self.id, institution__id=institution.id).exists()

    def get_institution_affiliation(self, institution_id):
        """Return the affiliation between the current user and a given institution by ``institution_id``."""
        try:
            return InstitutionAffiliation.objects.get(user__id=self.id, institution___id=institution_id)
        except InstitutionAffiliation.DoesNotExist:
            return None

    def has_affiliated_institutions(self):
        """Return if the current user is affiliated with any institutions."""
        return InstitutionAffiliation.objects.filter(user__id=self.id).exists()

    def get_affiliated_institutions(self):
        """Return a queryset of all affiliated institutions for the current user."""
        qs = InstitutionAffiliation.objects.filter(user__id=self.id).values_list('institution', flat=True)
        return Institution.objects.filter(pk__in=qs)

    def get_institution_affiliations(self):
        """Return a queryset of all institution affiliations for the current user."""
        return InstitutionAffiliation.objects.filter(user__id=self.id)

    def add_or_update_affiliated_institution(self, institution, sso_identity=None, sso_mail=None, sso_department=None):
        """Add one or update the existing institution affiliation between the current user and the given ``institution``
        with attributes. Returns the affiliation if created or updated; returns ``None`` if affiliation exists and
        there is nothing to update.
        """
        # CASE 1: affiliation not found -> create and return the affiliation
        if not self.is_affiliated_with_institution(institution):
            affiliation = InstitutionAffiliation.objects.create(
                user=self,
                institution=institution,
                sso_identity=sso_identity,
                sso_mail=sso_mail,
                sso_department=sso_department,
                sso_other_attributes={}
            )
            return affiliation
        # CASE 2: affiliation exists
        updated = False
        affiliation = InstitutionAffiliation.objects.get(user__id=self.id, institution__id=institution.id)
        if sso_department and affiliation.sso_department != sso_department:
            affiliation.sso_department = sso_department
            updated = True
        if sso_mail and affiliation.sso_mail != sso_mail:
            affiliation.sso_mail = sso_mail
            updated = True
        if sso_identity and affiliation.sso_identity != sso_identity:
            affiliation.sso_identity = sso_identity
            updated = True
        # CASE 1.1: nothing to update -> return None
        if not updated:
            return None
        # CASE 1.3: at least one attribute is updated -> return the affiliation
        affiliation.save()
        return affiliation

    def remove_sso_identity_from_affiliation(self, institution):
        if not self.is_affiliated_with_institution(institution):
            return None
        affiliation = InstitutionAffiliation.objects.get(user__id=self.id, institution__id=institution.id)
        affiliation.sso_identity = None
        affiliation.save()
        return affiliation

    def copy_institution_affiliation_when_merging_user(self, user):
        """Copy institution affiliations of the given ``user`` to the current user during merge."""
        affiliations = InstitutionAffiliation.objects.filter(user__id=user.id)
        for affiliation in affiliations:
            self.add_or_update_affiliated_institution(
                affiliation.institution,
                sso_identity=affiliation.sso_identity,
                sso_mail=affiliation.sso_mail,
                sso_department=affiliation.sso_department
            )

    def add_multiple_institutions_non_sso(self, institutions):
        """Add multiple affiliations for the user and a list of institutions, only used for email domain non-SSO."""
        for institution in institutions:
            self.add_or_update_affiliated_institution(
                institution,
                sso_identity=InstitutionAffiliation.DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE
            )

    def update_affiliated_institutions_by_email_domain(self):
        """Append affiliated_institutions by email domain."""
        try:
            email_domains = [email.split('@')[1].lower() for email in self.emails.values_list('address', flat=True)]
            institutions = Institution.objects.filter(email_domains__overlap=email_domains)
            if institutions.exists():
                self.add_multiple_institutions_non_sso(institutions)
        except IndexError:
            pass

    def remove_affiliated_institution(self, institution_id):
        """Remove the affiliation between the current user and a given institution by ``institution_id``."""
        affiliation = self.get_institution_affiliation(institution_id)
        if not affiliation:
            return False
        affiliation.delete()
        if self.has_perm('view_institutional_metrics', affiliation.institution):
            group = affiliation.institution.get_group('institutional_admins')
            group.user_set.remove(self)
            group.save()
        return True

    def remove_all_affiliated_institutions(self):
        """Remove all institution affiliations for the current user."""
        for institution in self.get_affiliated_institutions():
            self.remove_affiliated_institution(institution._id)

    def get_activity_points(self):
        return analytics.get_total_activity_count(self._id)

    def get_or_create_cookie(self, secret=None):
        """Find the cookie from the most recent session for the given user. Create a new session, compute its
        cookie value using the default or provide secret, and return the new cookie if no existing session is found.

        :param str secret: The key to sign the cookie with
        :returns: The signed cookie
        """
        secret = secret or website_settings.SECRET_KEY
        user_session_map = UserSessionMap.objects.filter(user__id=self.id, expire_date__gt=timezone.now()).order_by('-expire_date').first()
        if user_session_map and SessionStore().exists(session_key=user_session_map.session_key):
            user_session = SessionStore(session_key=user_session_map.session_key)
        else:
            user_session = SessionStore()
            user_session['auth_user_id'] = self._id
            user_session['auth_user_username'] = self.username
            user_session['auth_user_fullname'] = self.fullname
            user_session.create()
            UserSessionMap.objects.create(user=self, session_key=user_session.session_key)
        signer = itsdangerous.Signer(secret)
        return signer.sign(user_session.session_key)

    @classmethod
    def from_cookie(cls, cookie, secret=None):
        """Attempt to load a user from their signed cookie
        :returns: None if a user cannot be loaded else User
        """
        if not cookie:
            return None

        secret = secret or website_settings.SECRET_KEY

        try:
            session_key = ensure_str(itsdangerous.Signer(secret).unsign(cookie))
        except itsdangerous.BadSignature:
            return None

        if not SessionStore().exists(session_key=session_key):
            return None
        user_session = SessionStore(session_key=session_key)
        return cls.load(user_session.get('auth_user_id', None))

    def get_node_comment_timestamps(self, target_id):
        """ Returns the timestamp for when comments were last viewed on a node, file or wiki.
        """
        default_timestamp = dt.datetime(1970, 1, 1, 12, 0, 0, tzinfo=pytz.utc)
        return self.comments_viewed_timestamp.get(target_id, default_timestamp)

    def _get_spam_content(self, saved_fields=None, **unused_kwargs):
        """
        Retrieves content for spam checking from specified fields.
        Sometimes from validated serializer data, sometimes from
        dirty_fields.

        Parameters:
        - saved_fields (dict): Fields that have been saved and their values.
        - unused_kwargs: Ignored additional keyword arguments.

        Returns:
        - str: A string containing the spam check contents, joined by spaces.
        """
        # Determine which fields to check for spam, preferring saved_fields if provided.
        spam_check_fields = set(self.SPAM_USER_PROFILE_FIELDS)
        if saved_fields:
            spam_check_fields = set(saved_fields).intersection(spam_check_fields)

        spam_check_source = {field: getattr(self, field) for field in spam_check_fields}

        spam_contents = []
        for field in spam_check_fields:
            validated_data_from_serializer = spam_check_source.get(field)
            # Validated fields aren't from dirty_fields, they have values.
            if validated_data_from_serializer:
                spam_contents.extend(_get_nested_spam_check_content(spam_check_source, field))
            else:
                # these are the changed fields from dirty_fields, they have need current model values before saving.
                value = getattr(self, field, {})
                spam_contents.extend(_get_nested_spam_check_content(value, field))

        return ' '.join(spam_contents).strip()

    def check_spam(self, saved_fields, request_headers):
        is_spam = False
        content = self._get_spam_content(saved_fields)
        if content:
            is_spam = self.do_check_spam(
                self.fullname,
                self.username,
                content,
                request_headers
            )
            self.save()

        return is_spam

    def _get_addons_from_gv(self, requesting_user_id, service_type=None, auth=None):
        requesting_user = OSFUser.load(requesting_user_id)
        if requesting_user and requesting_user != self:
            raise ValueError('Cannot get user addons for a user other than self')

        all_user_account_data = gv_requests.iterate_accounts_for_user(
            requesting_user=self,
            addon_type=service_type,
        )
        for account_data in all_user_account_data:
            yield gv_translations.make_ephemeral_user_settings(
                gv_account_data=account_data,
                requesting_user=self,
            )

    def _validate_admin_status_for_gdpr_delete(self, resource):
        """
        Ensure that deleting the user won't leave the node without an admin.

        Args:
        - resource: An instance of a resource, probably AbstractNode or DraftRegistration.
        """
        alternate_admins = OSFUser.objects.filter(
            groups__name=resource.format_group(ADMIN),
            is_active=True
        ).exclude(id=self.id).exists()

        if not resource.deleted and not alternate_admins:
            raise UserStateError(
                f'You cannot delete {resource.__class__.__name__} {resource._id} because it would be '
                f'a {resource.__class__.__name__} with contributors, but with no admin.'
            )

    def _validate_addons_for_gdpr_delete(self, resource):
        """
        Ensure that the user's external accounts on the node won't cause issues upon deletion.

        Args:
        - resource: An instance of a resource, probably AbstractNode or DraftRegistration.
        """
        for addon in resource.get_addons():
            if addon.short_name not in ('osfstorage', 'wiki') and \
                    addon.user_settings and addon.user_settings.owner.id == self.id:
                raise UserStateError(
                    f'You cannot delete this user because they have an external account for {addon.short_name} '
                    f'attached to {resource.__class__.__name__} {resource._id}, which has other contributors.'
                )

    def gdpr_delete(self):
        """
        Complies with GDPR guidelines by disabling the account and removing identifying information.
        """

        # Check if user has something intentionally public, like preprints or registrations
        self._validate_no_public_entities()

        # Check if user has any non-registration AbstractNodes or DraftRegistrations that they might still share with
        # other contributors
        self._validate_and_remove_resource_for_gdpr_delete(
            self.nodes.exclude(type='osf.registration'),  # Includes DraftNodes and other typed nodes
            hard_delete=False
        )
        self._validate_and_remove_resource_for_gdpr_delete(
            self.draft_registrations.all(),
            hard_delete=True
        )

        # A Potentially out of date check that user isn't a member of a OSFGroup
        self._validate_osf_groups()

        # Finally delete the user's info.
        self._clear_identifying_information()

    def _validate_no_public_entities(self):
        """
        Ensure that the user doesn't have any public facing resources like Registrations or Preprints
        """
        from osf.models import Preprint

        if self.nodes.filter(deleted__isnull=True, type='osf.registration').exists():
            raise UserStateError('You cannot delete this user because they have one or more registrations.')

        if Preprint.objects.filter(_contributors=self, ever_public=True, deleted__isnull=True).exists():
            raise UserStateError('You cannot delete this user because they have one or more preprints.')

    def _validate_and_remove_resource_for_gdpr_delete(self, resources, hard_delete):
        """
        This method ensures a user's resources are properly deleted of using during GDPR delete request.

        Args:
        - resources: A queryset of resources probably of AbstractNode or DraftRegistration.
        - hard_delete: A boolean indicating whether the resource should be permentently deleted or just marked as such.
        """
        model = resources.query.model

        filter_deleted = {}
        if not hard_delete:
            filter_deleted = {'deleted__isnull': True}

        personal_resources = model.objects.annotate(
            contrib_count=Count('_contributors')
        ).filter(
            contrib_count__lte=1,
            _contributors=self
        ).filter(
            **filter_deleted
        )

        shared_resources = resources.exclude(id__in=personal_resources.values_list('id'))
        for node in shared_resources:
            self._validate_admin_status_for_gdpr_delete(node)
            self._validate_addons_for_gdpr_delete(node)

        for resource in shared_resources.all():
            logger.info(f'Removing {self._id} as a contributor to {resource.__class__.__name__} (pk:{resource.pk})...')
            resource.remove_contributor(self, auth=Auth(self), log=False)

        # Delete all personal entities
        for entity in personal_resources.all():
            if hard_delete:
                logger.info(f'Hard-deleting {entity.__class__.__name__} (pk: {entity.pk})...')
                entity.delete()
            else:
                logger.info(f'Soft-deleting {entity.__class__.__name__} (pk: {entity.pk})...')
                entity.remove_node(auth=Auth(self))

    def _validate_osf_groups(self):
        """
        This method ensures a user isn't in an OSFGroup before deleting them..
        """
        for group in self.osf_groups:
            if not group.managers.exclude(id=self.id).filter(is_registered=True).exists() and group.members.exclude(
                    id=self.id).exists():
                raise UserStateError(
                    f'You cannot delete this user because they are the only registered manager of OSFGroup {group._id} that contains other members.')
            elif len(group.managers) == 1 and group.managers[0] == self:
                group.remove_group()
            else:
                group.remove_member(self)

    def _clear_identifying_information(self):
        '''
        This method ensures a user's info is deleted during a GDPR delete
        '''
        # This doesn't remove identifying info, but ensures other users can't see the deleted user's profile etc.
        self.deactivate_account()

        logger.info('Clearing identifying information...')
        # This removes identifying info
        # hard-delete all emails associated with the user
        self.emails.all().delete()
        # Change name to "Deleted user" so that logs render properly
        self.fullname = 'Deleted user'
        self.set_unusable_username()
        self.set_unusable_password()
        self.given_name = ''
        self.family_name = ''
        self.middle_names = ''
        self.mailchimp_mailing_lists = {}
        self.osf_mailing_lists = {}
        self.verification_key = None
        self.suffix = ''
        self.jobs = []
        self.schools = []
        self.social = {}
        self.unclaimed_records = {}
        self.notifications_configured = {}
        # Scrub all external accounts
        if self.external_accounts.exists():
            logger.info('Clearing identifying information from external accounts...')
            for account in self.external_accounts.all():
                account.oauth_key = None
                account.oauth_secret = None
                account.refresh_token = None
                account.provider_name = 'gdpr-deleted'
                account.display_name = None
                account.profile_url = None
                account.save()
            self.external_accounts.clear()
        self.external_identity = {}
        self.deleted = timezone.now()

    @property
    def has_resources(self):
        """
        This is meant to determine if a user has any resources, nodes, preprints etc that might impede their deactivation.
        If a user only has no resources or only deleted resources this will return false and they can safely be deactivated
        otherwise they must delete or transfer their outstanding resources.

        :return bool: does the user have any active node, preprints, groups, etc?
        """
        from osf.models import Preprint

        nodes = self.nodes.filter(deleted__isnull=True).exists()
        groups = self.osf_groups.exists()
        preprints = Preprint.objects.filter(_contributors=self, ever_public=True, deleted__isnull=True).exists()

        return groups or nodes or preprints

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            # Clashes with built-in permissions
            # ('view_osfuser', 'Can view user details'),
        )

@receiver(post_save, sender=OSFUser)
def add_default_user_addons(sender, instance, created, **kwargs):
    if created:
        for addon in website_settings.ADDONS_AVAILABLE:
            if 'user' in addon.added_default:
                instance.add_addon(addon.short_name)

@receiver(post_save, sender=OSFUser)
def create_bookmark_collection(sender, instance, created, **kwargs):
    if created:
        new_bookmark_collection(instance)


def _get_nested_spam_check_content(spam_check_source, field_name):
    """
    Social fields are formatted differently when coming from the serializer or save
    """
    if spam_check_source:
        if field_name == 'social':
            # Attempt to extract from the nested 'social' field first, then fall back to 'profileWebsites'.
            data = spam_check_source.get('profileWebsites', [])
            return spam_check_source.get('social', {}).get('profileWebsites', []) or data

    spam_check_content = []
    if spam_check_source and isinstance(spam_check_source, dict):
        # Ensure spam_check_source[field_name] is always a list for uniform processing
        source_data = spam_check_source.get(field_name, [])
        if not isinstance(source_data, list):
            source_data = [source_data]
    elif spam_check_source and not isinstance(spam_check_source, dict):
        source_data = spam_check_source
    else:
        return spam_check_content

    keys = OSFUser.SPAM_USER_PROFILE_FIELDS.get(field_name, [])
    for data in source_data:
        for key in keys:
            if data.get(key):
                spam_check_content.append(data[key])

    return spam_check_content
