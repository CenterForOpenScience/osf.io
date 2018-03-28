import datetime as dt
import logging
import re
import urllib
import urlparse
import uuid
from copy import deepcopy
from os.path import splitext

from flask import Request as FlaskRequest
from framework import analytics

# OSF imports
import itsdangerous
import pytz
from dirtyfields import DirtyFieldsMixin

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import PermissionsMixin
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.utils import timezone

from framework.auth import Auth, signals, utils
from framework.auth.core import generate_verification_key
from framework.auth.exceptions import (ChangePasswordError, ExpiredTokenError,
                                       InvalidTokenError,
                                       MergeConfirmedRequiredError,
                                       MergeConflictError)
from framework.exceptions import PermissionsError
from framework.sessions.utils import remove_sessions_for_user
from osf.utils.requests import get_current_request
from osf.exceptions import reraise_django_validation_errors, MaxRetriesError
from osf.models.base import BaseModel, GuidMixin, GuidMixinQuerySet
from osf.models.contributor import Contributor, RecentlyAddedContributor
from osf.models.institution import Institution
from osf.models.mixins import AddonModelMixin
from osf.models.session import Session
from osf.models.tag import Tag
from osf.models.validators import validate_email, validate_social, validate_history_item
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField, LowercaseEmailField
from osf.utils.names import impute_names
from osf.utils.requests import check_select_for_update
from website import settings as website_settings
from website import filters, mails
from website.project import new_bookmark_collection

logger = logging.getLogger(__name__)

MAX_QUICKFILES_MERGE_RENAME_ATTEMPTS = 1000

def get_default_mailing_lists():
    return {'Open Science Framework Help': True}


name_formatters = {
    'long': lambda user: user.fullname,
    'surname': lambda user: user.family_name if user.family_name else user.fullname,
    'initials': lambda user: u'{surname}, {initial}.'.format(
        surname=user.family_name,
        initial=user.given_name_initial,
    ),
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


class OSFUser(DirtyFieldsMixin, GuidMixin, BaseModel, AbstractBaseUser, PermissionsMixin, AddonModelMixin):
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
    }
    TRACK_FIELDS = SEARCH_UPDATE_FIELDS.copy()
    TRACK_FIELDS.update({'password', 'last_login'})

    # TODO: Add SEARCH_UPDATE_NODE_FIELDS, for fields that should trigger a
    #   search update for all nodes to which the user is a contributor.

    SOCIAL_FIELDS = {
        'orcid': u'http://orcid.org/{}',
        'github': u'http://github.com/{}',
        'scholar': u'http://scholar.google.com/citations?user={}',
        'twitter': u'http://twitter.com/{}',
        'profileWebsites': [],
        'linkedIn': u'https://www.linkedin.com/{}',
        'impactStory': u'https://impactstory.org/u/{}',
        'researcherId': u'http://researcherid.com/rid/{}',
        'researchGate': u'https://researchgate.net/profile/{}',
        'academiaInstitution': u'https://{}',
        'academiaProfileID': u'.academia.edu/{}',
        'baiduScholar': u'http://xueshu.baidu.com/scholarID/{}',
        'ssrn': u'http://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id={}'
    }

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

    # user has claimed the account
    # TODO: This should be retired - it always reflects is_registered.
    #   While a few entries exist where this is not the case, they appear to be
    #   the result of a bug, as they were all created over a small time span.
    is_claimed = models.BooleanField(default=False, db_index=True)

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

    # The user into which this account was merged
    merged_by = models.ForeignKey('self', null=True, blank=True, related_name='merger')

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
    #     'twitter': <twitter id>,
    # }

    # date the user last sent a request
    date_last_login = NonNaiveDateTimeField(null=True, blank=True)

    # date the user first successfully confirmed an email address
    date_confirmed = NonNaiveDateTimeField(db_index=True, null=True, blank=True)

    # When the user was disabled.
    date_disabled = NonNaiveDateTimeField(db_index=True, null=True, blank=True)

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

    affiliated_institutions = models.ManyToManyField('Institution', blank=True)

    notifications_configured = DateTimeAwareJSONField(default=dict, blank=True)

    objects = OSFUserManager()

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    def __repr__(self):
        return '<OSFUser({0!r}) with guid {1!r}>'.format(self.username, self._id)

    @property
    def deep_url(self):
        """Used for GUID resolution."""
        return '/profile/{}/'.format(self._primary_key)

    @property
    def url(self):
        return '/{}/'.format(self._id)

    @property
    def absolute_url(self):
        return urlparse.urljoin(website_settings.DOMAIN, self.url)

    @property
    def absolute_api_v2_url(self):
        from website import util
        return util.api_v2_url('users/{}/'.format(self._id))

    @property
    def api_url(self):
        return '/api/v1/profile/{}/'.format(self._id)

    @property
    def profile_url(self):
        return '/{}/'.format(self._id)

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
        social_user_fields = {}
        for key, val in self.social.items():
            if val and key in self.SOCIAL_FIELDS:
                if not isinstance(val, basestring):
                    social_user_fields[key] = val
                else:
                    social_user_fields[key] = self.SOCIAL_FIELDS[key].format(val)
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

        if self.family_name and self.given_name:
            """If the user has a family and given name, use those"""
            return {
                'family': self.family_name,
                'given': self.csl_given_name,
            }
        else:
            """ If the user doesn't autofill his family and given name """
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
    def contributor_to(self):
        return self.nodes.filter(is_deleted=False, type__in=['osf.node', 'osf.registration'])

    @property
    def visible_contributor_to(self):
        return self.nodes.filter(is_deleted=False, contributor__visible=True, type__in=['osf.node', 'osf.registration'])

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

    @property
    def contributed(self):
        return self.nodes.all()

    @property
    def can_be_merged(self):
        """The ability of the `merge_user` method to fully merge the user"""
        return all((addon.can_be_merged for addon in self.get_addons()))

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

        # Fail if the other user has conflicts.
        if not user.can_be_merged:
            raise MergeConflictError('Users cannot be merged')
        # Move over the other user's attributes
        # TODO: confirm
        for system_tag in user.system_tags.all():
            self.add_system_tag(system_tag)

        self.is_claimed = self.is_claimed or user.is_claimed
        self.is_invited = self.is_invited or user.is_invited

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
        if not website_settings.RUNNING_MIGRATION:
            for key, value in user.mailchimp_mailing_lists.iteritems():
                # subscribe to each list if either user was subscribed
                subscription = value or self.mailchimp_mailing_lists.get(key)
                signals.user_merged.send(self, list_name=key, subscription=subscription)

                # clear subscriptions for merged user
                signals.user_merged.send(user, list_name=key, subscription=False, send_goodbye=False)

        for target_id, timestamp in user.comments_viewed_timestamp.iteritems():
            if not self.comments_viewed_timestamp.get(target_id):
                self.comments_viewed_timestamp[target_id] = timestamp
            elif timestamp > self.comments_viewed_timestamp[target_id]:
                self.comments_viewed_timestamp[target_id] = timestamp

        # Give old user's emails to self
        user.emails.update(user=self)

        for k, v in user.email_verifications.iteritems():
            email_to_confirm = v['email']
            if k not in self.email_verifications and email_to_confirm != user.username:
                self.email_verifications[k] = v
        user.email_verifications = {}

        self.affiliated_institutions.add(*user.affiliated_institutions.values_list('pk', flat=True))

        for service in user.external_identity:
            for service_id in user.external_identity[service].iterkeys():
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

        # - addons
        # Note: This must occur before the merged user is removed as a
        #       contributor on the nodes, as an event hook is otherwise fired
        #       which removes the credentials.
        for addon in user.get_addons():
            user_settings = self.get_or_add_addon(addon.config.short_name)
            user_settings.merge(addon)
            user_settings.save()

        # - projects where the user was a contributor
        for node in user.contributed:
            # Skip quickfiles
            if node.is_quickfiles:
                continue
            # if both accounts are contributor of the same project
            if node.is_contributor(self) and node.is_contributor(user):
                user_permissions = node.get_permissions(user)
                self_permissions = node.get_permissions(self)
                permissions = max([user_permissions, self_permissions])
                node.set_permissions(user=self, permissions=permissions)

                visible1 = self._id in node.visible_contributor_ids
                visible2 = user._id in node.visible_contributor_ids
                if visible1 != visible2:
                    node.set_visible(user=self, visible=True, log=True, auth=Auth(user=self))

                node.contributor_set.filter(user=user).delete()
            else:
                node.contributor_set.filter(user=user).update(user=self)

            node.save()

        # Skip bookmark collections
        user.collection_set.exclude(is_bookmark_collection=True).update(creator=self)

        from osf.models import QuickFilesNode
        from osf.models import BaseFileNode

        # - projects where the user was the creator
        user.nodes_created.exclude(type=QuickFilesNode._typedmodels_type).update(creator=self)

        # - file that the user has checked_out, import done here to prevent import error
        for file_node in BaseFileNode.files_checked_out(user=user):
            file_node.checkout = self
            file_node.save()

        # - move files in the merged user's quickfiles node, checking for name conflicts
        from addons.osfstorage.models import OsfStorageFileNode
        primary_quickfiles = QuickFilesNode.objects.get(creator=self)
        merging_user_quickfiles = QuickFilesNode.objects.get(creator=user)

        files_in_merging_user_quickfiles = merging_user_quickfiles.files.filter(type='osf.osfstoragefile')
        for merging_user_file in files_in_merging_user_quickfiles:
            if OsfStorageFileNode.objects.filter(node=primary_quickfiles, name=merging_user_file.name).exists():
                digit = 1
                split_filename = splitext(merging_user_file.name)
                name_without_extension = split_filename[0]
                extension = split_filename[1]
                found_digit_in_parens = re.findall('(?<=\()(\d)(?=\))', name_without_extension)
                if found_digit_in_parens:
                    found_digit = int(found_digit_in_parens[0])
                    digit = found_digit + 1
                    name_without_extension = name_without_extension.replace('({})'.format(found_digit), '').strip()
                new_name_format = '{} ({}){}'
                new_name = new_name_format.format(name_without_extension, digit, extension)

                # check if new name conflicts, update til it does not (try up to 1000 times)
                rename_count = 0
                while OsfStorageFileNode.objects.filter(node=primary_quickfiles, name=new_name).exists():
                    digit += 1
                    new_name = new_name_format.format(name_without_extension, digit, extension)
                    rename_count += 1
                    if rename_count >= MAX_QUICKFILES_MERGE_RENAME_ATTEMPTS:
                        raise MaxRetriesError('Maximum number of rename attempts has been reached')

                merging_user_file.name = new_name
                merging_user_file.save()

            merging_user_file.node = primary_quickfiles
            merging_user_file.save()

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

    def disable_account(self):
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
        except mailchimp_utils.mailchimp.ListNotSubscribedError:
            pass
        except mailchimp_utils.mailchimp.InvalidApiKeyError:
            if not website_settings.ENABLE_EMAIL_SUBSCRIPTIONS:
                pass
            else:
                raise
        except mailchimp_utils.mailchimp.EmailNotExistsError:
            pass
        # Call to `unsubscribe` above saves, and can lead to stale data
        self.reload()
        self.is_disabled = True

        # we must call both methods to ensure the current session is cleared and all existing
        # sessions are revoked.
        req = get_current_request()
        if isinstance(req, FlaskRequest):
            logout()
        remove_sessions_for_user(self)

    def update_is_active(self):
        """Update ``is_active`` to be consistent with the fields that
        it depends on.
        """
        # The user can log in if they have set a password OR
        # have a verified external ID, e.g an ORCID
        can_login = self.has_usable_password() or (
            'VERIFIED' in sum([each.values() for each in self.external_identity.values()], [])
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
        self.update_is_active()
        self.username = self.username.lower().strip() if self.username else None
        dirty_fields = set(self.get_dirty_fields(check_relationship=True))
        ret = super(OSFUser, self).save(*args, **kwargs)
        if self.SEARCH_UPDATE_FIELDS.intersection(dirty_fields) and self.is_confirmed:
            self.update_search()
            self.update_search_nodes_contributors()
        if 'fullname' in dirty_fields:
            from osf.models.quickfiles import get_quickfiles_project_title, QuickFilesNode

            quickfiles = QuickFilesNode.objects.filter(creator=self).first()
            if quickfiles:
                quickfiles.title = get_quickfiles_project_title(self)
                quickfiles.save()
        return ret

    # Legacy methods

    @classmethod
    def create(cls, username, password, fullname):
        validate_email(username)  # Raises ValidationError if spam address

        user = cls(
            username=username,
            fullname=fullname,
        )
        user.update_guessed_names()
        user.set_password(password)
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
        super(OSFUser, self).set_password(raw_password)
        if had_existing_password and notify:
            mails.send_mail(
                to_addr=self.username,
                mail=mails.PASSWORD_RESET,
                mimetype='plain',
                user=self,
                osf_contact_email=website_settings.OSF_CONTACT_EMAIL
            )
            remove_sessions_for_user(self)

    @classmethod
    def create_unconfirmed(cls, username, password, fullname, external_identity=None,
                           do_confirm=True, campaign=None):
        """Create a new user who has begun registration but needs to verify
        their primary email address (username).
        """
        user = cls.create(username, password, fullname)
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
        return user

    @classmethod
    def create_confirmed(cls, username, password, fullname):
        user = cls.create(username, password, fullname)
        user.is_registered = True
        user.is_claimed = True
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
            for token, value in self.email_verifications.iteritems():
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

    def add_unconfirmed_email(self, email, expiration=None, external_identity=None):
        """
        Add an email verification token for a given email.

        :param email: the email to confirm
        :param email: overwrite default expiration time
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
        for token, value in self.email_verifications.iteritems():
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
                    new_token = self.add_unconfirmed_email(email)
                    self.save()
                    return new_token
                if not expiration or (expiration and expiration < timezone.now()):
                    if not force:
                        raise ExpiredTokenError('Token for email "{0}" is expired'.format(email))
                    else:
                        new_token = self.add_unconfirmed_email(email)
                        self.save()
                        return new_token
                return token
        raise KeyError('No confirmation token for email "{0}"'.format(email))

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
        destination = '?{}'.format(urllib.urlencode({'destination': destination})) if destination else ''
        return '{0}confirm/{1}{2}/{3}/{4}'.format(base, external, self._primary_key, token, destination)

    def register(self, username, password=None):
        """Registers the user.
        """
        self.username = username
        if password:
            self.set_password(password)
        if not self.emails.filter(address=username):
            self.emails.create(address=username)
        self.is_registered = True
        self.is_claimed = True
        self.date_confirmed = timezone.now()
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
                user_to_merge = OSFUser.objects.filter(emails__address=email).select_for_update().get()
            else:
                user_to_merge = OSFUser.objects.get(emails__address=email)
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
            unregistered_user = OSFUser.objects.exclude(guids___id=self._id).get(username=email)
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

    def update_search(self):
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
        for node in self.contributor_to:
            node.update_search()

    def update_date_last_login(self):
        self.date_last_login = timezone.now()

    def get_summary(self, formatter='long'):
        return {
            'user_fullname': self.fullname,
            'user_profile_url': self.profile_url,
            'user_display_name': name_formatters[formatter](self),
            'user_is_claimed': self.is_claimed
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
        sqs = Contributor.objects.filter(node=models.OuterRef('pk'), user=other_user)
        return (self.nodes
                 .filter(is_deleted=False)
                 .exclude(type='osf.collection')
                 .annotate(contrib=models.Exists(sqs))
                 .filter(contrib=True))

    def get_projects_in_common(self, other_user):
        """Returns either a collection of "shared projects" (projects that both users are contributors for)
        or just their primary keys
        """
        query = self._projects_in_common_query(other_user)
        return set(query.all())

    def n_projects_in_common(self, other_user):
        """Returns number of "shared projects" (projects that both users are contributors for)"""
        return self._projects_in_common_query(other_user).count()

    def add_unclaimed_record(self, node, referrer, given_name, email=None):
        """Add a new project entry in the unclaimed records dictionary.

        :param Node node: Node this unclaimed user was added to.
        :param User referrer: User who referred this user.
        :param str given_name: The full name that the referrer gave for this user.
        :param str email: The given email address.
        :returns: The added record
        """
        if not node.can_edit(user=referrer):
            raise PermissionsError(
                'Referrer does not have permission to add a contributor to project {0}'.format(node._primary_key)
            )
        project_id = str(node._id)
        referrer_id = str(referrer._id)
        if email:
            clean_email = email.lower().strip()
        else:
            clean_email = None
        verification_key = generate_verification_key(verification_type='claim')
        try:
            record = self.unclaimed_records[node._id]
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
        self.unclaimed_records[project_id] = record
        return record

    def get_unclaimed_record(self, project_id):
        """Get an unclaimed record for a given project_id.

        :raises: ValueError if there is no record for the given project.
        """
        try:
            return self.unclaimed_records[project_id]
        except KeyError:  # reraise as ValueError
            raise ValueError('No unclaimed record for user {self._id} on node {project_id}'
                                .format(**locals()))

    def get_claim_url(self, project_id, external=False):
        """Return the URL that an unclaimed user should use to claim their
        account. Return ``None`` if there is no unclaimed_record for the given
        project ID.

        :param project_id: The project ID for the unclaimed record
        :raises: ValueError if a record doesn't exist for the given project ID
        :rtype: dict
        :returns: The unclaimed record for the project
        """
        uid = self._primary_key
        base_url = website_settings.DOMAIN if external else '/'
        unclaimed_record = self.get_unclaimed_record(project_id)
        token = unclaimed_record['token']
        return '{base_url}user/{uid}/{project_id}/claim/?token={token}'\
                    .format(**locals())

    def is_affiliated_with_institution(self, institution):
        """Return if this user is affiliated with ``institution``."""
        return self.affiliated_institutions.filter(id=institution.id).exists()

    def update_affiliated_institutions_by_email_domain(self):
        """
        Append affiliated_institutions by email domain.
        :return:
        """
        try:
            email_domains = [email.split('@')[1].lower() for email in self.emails.values_list('address', flat=True)]
            insts = Institution.objects.filter(email_domains__overlap=email_domains)
            if insts.exists():
                self.affiliated_institutions.add(*insts)
        except IndexError:
            pass

    def remove_institution(self, inst_id):
        try:
            inst = self.affiliated_institutions.get(_id=inst_id)
        except Institution.DoesNotExist:
            return False
        else:
            self.affiliated_institutions.remove(inst)
            return True

    def get_activity_points(self):
        return analytics.get_total_activity_count(self._id)

    def get_or_create_cookie(self, secret=None):
        """Find the cookie for the given user
        Create a new session if no cookie is found

        :param str secret: The key to sign the cookie with
        :returns: The signed cookie
        """
        secret = secret or settings.SECRET_KEY
        user_session = Session.objects.filter(
            data__auth_user_id=self._id
        ).order_by(
            '-modified'
        ).first()

        if not user_session:
            user_session = Session(data={
                'auth_user_id': self._id,
                'auth_user_username': self.username,
                'auth_user_fullname': self.fullname,
            })
            user_session.save()

        signer = itsdangerous.Signer(secret)
        return signer.sign(user_session._id)

    @classmethod
    def from_cookie(cls, cookie, secret=None):
        """Attempt to load a user from their signed cookie
        :returns: None if a user cannot be loaded else User
        """
        if not cookie:
            return None

        secret = secret or settings.SECRET_KEY

        try:
            token = itsdangerous.Signer(secret).unsign(cookie)
        except itsdangerous.BadSignature:
            return None

        user_session = Session.load(token)

        if user_session is None:
            return None

        return cls.load(user_session.data.get('auth_user_id'))

    def get_node_comment_timestamps(self, target_id):
        """ Returns the timestamp for when comments were last viewed on a node, file or wiki.
        """
        default_timestamp = dt.datetime(1970, 1, 1, 12, 0, 0, tzinfo=pytz.utc)
        return self.comments_viewed_timestamp.get(target_id, default_timestamp)

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            ('view_osfuser', 'Can view user details'),
        )

@receiver(post_save, sender=OSFUser)
def create_bookmark_collection(sender, instance, created, **kwargs):
    if created:
        new_bookmark_collection(instance)


@receiver(post_save, sender=OSFUser)
def create_quickfiles_project(sender, instance, created, **kwargs):
    from osf.models.quickfiles import QuickFilesNode

    if created:
        QuickFilesNode.objects.create_for_user(instance)
