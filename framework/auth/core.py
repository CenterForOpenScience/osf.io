# -*- coding: utf-8 -*-
import re
import logging
import urlparse
import itertools
import datetime as dt

import bson
import pytz
import itsdangerous

from modularodm import fields, Q
from modularodm.validators import URLValidator
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationError, ValidationValueError

import framework
from framework import analytics
from framework.sessions import session
from framework.auth import exceptions, utils, signals
from framework.sentry import log_exception
from framework.addons import AddonModelMixin
from framework.sessions.model import Session
from framework.sessions.utils import remove_sessions_for_user
from framework.exceptions import PermissionsError
from framework.guid.model import GuidStoredObject
from framework.bcrypt import generate_password_hash, check_password_hash
from framework.auth.exceptions import ChangePasswordError, ExpiredTokenError

from website import mails, settings, filters, security


name_formatters = {
    'long': lambda user: user.fullname,
    'surname': lambda user: user.family_name if user.family_name else user.fullname,
    'initials': lambda user: u'{surname}, {initial}.'.format(
        surname=user.family_name,
        initial=user.given_name_initial,
    ),
}

logger = logging.getLogger(__name__)

# Hide implementation of token generation
def generate_confirm_token():
    return security.random_string(30)


def generate_claim_token():
    return security.random_string(30)


def string_required(value):
    if value is None or value == '':
        raise ValidationValueError('Value must not be empty.')


def validate_history_item(item):
    startMonth = item.get('startMonth')
    startYear = item.get('startYear')
    endMonth = item.get('endMonth')
    endYear = item.get('endYear')

    validate_year(startYear)
    validate_year(endYear)

    if startYear and endYear:
        if endYear < startYear:
            raise ValidationValueError('End date must be later than start date.')
        elif endYear == startYear:
            if endMonth and startMonth and endMonth < startMonth:
                raise ValidationValueError('End date must be later than start date.')


def validate_year(item):
    if item:
        try:
            int(item)
        except ValueError:
            raise ValidationValueError('Please enter a valid year.')
        else:
            if len(item) != 4:
                raise ValidationValueError('Please enter a valid year.')


validate_url = URLValidator()
def validate_personal_site(value):
    if value:
        try:
            validate_url(value)
        except ValidationError:
            # Reraise with a better message
            raise ValidationError('Invalid personal URL.')


def validate_social(value):
    validate_personal_site(value.get('personal'))


def validate_email(item):
    if not (item
            and re.match(r'^.+@[^.].*\.[a-z]{2,10}$', item, re.IGNORECASE)
            and item == item.strip().lower()):
        raise ValidationError("Invalid Email")


# TODO - rename to _get_current_user_from_session /HRYBACKI
def _get_current_user():
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return User.load(uid)


# TODO: This should be a class method of User?
def get_user(email=None, password=None, verification_key=None):
    """Get an instance of User matching the provided params.

    :return: The instance of User requested
    :rtype: User or None
    """
    # tag: database
    if password and not email:
        raise AssertionError("If a password is provided, an email must also "
                             "be provided.")

    query_list = []
    if email:
        email = email.strip().lower()
        query_list.append(Q('emails', 'eq', email) | Q('username', 'eq', email))
    if password:
        password = password.strip()
        try:
            query = query_list[0]
            for query_part in query_list[1:]:
                query = query & query_part
            user = User.find_one(query)
        except Exception as err:
            logger.error(err)
            user = None
        if user and not user.check_password(password):
            return False
        return user
    if verification_key:
        query_list.append(Q('verification_key', 'eq', verification_key))
    try:
        query = query_list[0]
        for query_part in query_list[1:]:
            query = query & query_part
        user = User.find_one(query)
        return user
    except Exception as err:
        logger.error(err)
        return None


class Auth(object):

    def __init__(self, user=None, api_node=None,
                 private_key=None):
        self.user = user
        self.api_node = api_node
        self.private_key = private_key

    def __repr__(self):
        return ('<Auth(user="{self.user}", '
                'private_key={self.private_key})>').format(self=self)

    @property
    def logged_in(self):
        return self.user is not None

    @classmethod
    def from_kwargs(cls, request_args, kwargs):
        user = request_args.get('user') or kwargs.get('user') or _get_current_user()
        private_key = request_args.get('view_only')

        return cls(
            user=user,
            private_key=private_key,
        )


class User(GuidStoredObject, AddonModelMixin):

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

    # TODO: Add SEARCH_UPDATE_NODE_FIELDS, for fields that should trigger a
    #   search update for all nodes to which the user is a contributor.

    SOCIAL_FIELDS = {
        'orcid': u'http://orcid.com/{}',
        'github': u'http://github.com/{}',
        'scholar': u'http://scholar.google.com/citation?user={}',
        'twitter': u'http://twitter.com/{}',
        'personal': u'{}',
        'linkedIn': u'https://www.linkedin.com/profile/view?id={}',
        'impactStory': u'https://impactstory.org/{}',
        'researcherId': u'http://researcherid.com/rid/{}',
    }

    # This is a GuidStoredObject, so this will be a GUID.
    _id = fields.StringField(primary=True)

    # The primary email address for the account.
    # This value is unique, but multiple "None" records exist for:
    #   * unregistered contributors where an email address was not provided.
    # TODO: Update mailchimp subscription on username change in user.save()
    username = fields.StringField(required=False, unique=True, index=True)

    # Hashed. Use `User.set_password` and `User.check_password`
    password = fields.StringField()

    fullname = fields.StringField(required=True, validate=string_required)

    # user has taken action to register the account
    is_registered = fields.BooleanField(index=True)

    # user has claimed the account
    # TODO: This should be retired - it always reflects is_registered.
    #   While a few entries exist where this is not the case, they appear to be
    #   the result of a bug, as they were all created over a small time span.
    is_claimed = fields.BooleanField(default=False, index=True)

    # a list of strings - for internal use
    system_tags = fields.StringField(list=True)

    # security emails that have been sent
    # TODO: This should be removed and/or merged with system_tags
    security_messages = fields.DictionaryField()
    # Format: {
    #   <message label>: <datetime>
    #   ...
    # }

    # user was invited (as opposed to registered unprompted)
    is_invited = fields.BooleanField(default=False, index=True)

    # Per-project unclaimed user data:
    # TODO: add validation
    unclaimed_records = fields.DictionaryField(required=False)
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

    # The user into which this account was merged
    merged_by = fields.ForeignField('user',
                                    default=None,
                                    backref='merged',
                                    index=True)

    # verification key used for resetting password
    verification_key = fields.StringField()

    # confirmed emails
    #   emails should be stripped of whitespace and lower-cased before appending
    # TODO: Add validator to ensure an email address only exists once across
    # all User's email lists
    emails = fields.StringField(list=True)

    # email verification tokens
    #   see also ``unconfirmed_emails``
    email_verifications = fields.DictionaryField(default=dict)
    # Format: {
    #   <token> : {'email': <email address>,
    #              'expiration': <datetime>}
    # }

    # email lists to which the user has chosen a subscription setting
    mailing_lists = fields.DictionaryField()
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # the date this user was registered
    # TODO: consider removal - this can be derived from date_registered
    date_registered = fields.DateTimeField(auto_now_add=dt.datetime.utcnow,
                                           index=True)

    # watched nodes are stored via a list of WatchConfigs
    watched = fields.ForeignField("WatchConfig", list=True, backref="watched")

    # list of users recently added to nodes as a contributor
    recently_added = fields.ForeignField("user", list=True, backref="recently_added")

    # Attached external accounts (OAuth)
    external_accounts = fields.ForeignField("externalaccount",
                                            list=True,
                                            backref="connected")

    # CSL names
    given_name = fields.StringField()
    middle_names = fields.StringField()
    family_name = fields.StringField()
    suffix = fields.StringField()

    # Employment history
    jobs = fields.DictionaryField(list=True, validate=validate_history_item)
    # Format: {
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
    schools = fields.DictionaryField(list=True, validate=validate_history_item)
    # Format: {
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
    social = fields.DictionaryField(validate=validate_social)
    # Format: {
    #     'personal': <personal site>,
    #     'twitter': <twitter id>,
    # }

    # hashed password used to authenticate to Piwik
    piwik_token = fields.StringField()

    # date the user last logged in via the web interface
    date_last_login = fields.DateTimeField()

    # date the user first successfully confirmed an email address
    date_confirmed = fields.DateTimeField(index=True)

    # When the user was disabled.
    date_disabled = fields.DateTimeField(index=True)

    # when comments for a node were last viewed
    comments_viewed_timestamp = fields.DictionaryField()
    # Format: {
    #   'node_id': 'timestamp'
    # }

    # timezone for user's locale (e.g. 'America/New_York')
    timezone = fields.StringField(default='Etc/UTC')

    # user language and locale data (e.g. 'en_US')
    locale = fields.StringField(default='en_US')

    _meta = {'optimistic': True}

    def __repr__(self):
        return '<User({0!r}) with id {1!r}>'.format(self.username, self._id)

    def __str__(self):
        return self.fullname.encode('ascii', 'replace')

    __unicode__ = __str__

    # For compatibility with Django auth
    @property
    def pk(self):
        return self._id

    @property
    def email(self):
        return self.username

    def is_authenticated(self):  # Needed for django compat
        return True

    def is_anonymous(self):
        return False

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse  # Avoid circular dependency
        return absolute_reverse('users:user-detail', kwargs={'user_id': self.pk})

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

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
        user.update_guessed_names()
        return user

    @classmethod
    def create(cls, username, password, fullname):
        user = cls(
            username=username,
            fullname=fullname,
        )
        user.update_guessed_names()
        user.set_password(password)
        return user

    @classmethod
    def create_unconfirmed(cls, username, password, fullname, do_confirm=True):
        """Create a new user who has begun registration but needs to verify
        their primary email address (username).
        """
        user = cls.create(username, password, fullname)
        user.add_unconfirmed_email(username)
        user.is_registered = False
        return user

    @classmethod
    def create_confirmed(cls, username, password, fullname):
        user = cls.create(username, password, fullname)
        user.is_registered = True
        user.is_claimed = True
        user.date_confirmed = user.date_registered
        return user

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

    def get_or_create_cookie(self, secret=None):
        """Find the cookie for the given user
        Create a new session if no cookie is found

        :param str secret: The key to sign the cookie with
        :returns: The signed cookie
        """
        secret = secret or settings.SECRET_KEY
        sessions = Session.find(
            Q('data.auth_user_id', 'eq', self._id)
        ).sort(
            '-date_modified'
        ).limit(1)

        if sessions.count() > 0:
            user_session = sessions[0]
        else:
            user_session = Session(data={
                'auth_user_id': self._id,
                'auth_user_username': self.username,
                'auth_user_fullname': self.fullname,
            })
            user_session.save()

        signer = itsdangerous.Signer(secret)
        return signer.sign(user_session._id)

    def update_guessed_names(self):
        """Updates the CSL name fields inferred from the the full name.
        """
        parsed = utils.impute_names(self.fullname)
        self.given_name = parsed['given']
        self.middle_names = parsed['middle']
        self.family_name = parsed['family']
        self.suffix = parsed['suffix']

    def register(self, username, password=None):
        """Registers the user.
        """
        self.username = username
        if password:
            self.set_password(password)
        if username not in self.emails:
            self.emails.append(username)
        self.is_registered = True
        self.is_claimed = True
        self.date_confirmed = dt.datetime.utcnow()
        self.update_search()
        self.update_search_nodes()

        # Emit signal that a user has confirmed
        signals.user_confirmed.send(self)

        return self

    def add_unclaimed_record(self, node, referrer, given_name, email=None):
        """Add a new project entry in the unclaimed records dictionary.

        :param Node node: Node this unclaimed user was added to.
        :param User referrer: User who referred this user.
        :param str given_name: The full name that the referrer gave for this user.
        :param str email: The given email address.
        :returns: The added record
        """
        if not node.can_edit(user=referrer):
            raise PermissionsError('Referrer does not have permission to add a contributor '
                'to project {0}'.format(node._primary_key))
        project_id = node._primary_key
        referrer_id = referrer._primary_key
        if email:
            clean_email = email.lower().strip()
        else:
            clean_email = None
        record = {
            'name': given_name,
            'referrer_id': referrer_id,
            'token': generate_confirm_token(),
            'email': clean_email
        }
        self.unclaimed_records[project_id] = record
        return record

    def display_full_name(self, node=None):
        """Return the full name , as it would display in a contributor list for a
        given node.

        NOTE: Unclaimed users may have a different name for different nodes.
        """
        if node:
            unclaimed_data = self.unclaimed_records.get(node._primary_key, None)
            if unclaimed_data:
                return unclaimed_data['name']
        return self.fullname

    @property
    def is_active(self):
        """Returns True if the user is active. The user must have activated
        their account, must not be deleted, suspended, etc.

        :return: bool
        """
        return (self.is_registered and
                self.password is not None and
                not self.is_merged and
                not self.is_disabled and
                self.is_confirmed)

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
        base_url = settings.DOMAIN if external else '/'
        unclaimed_record = self.get_unclaimed_record(project_id)
        token = unclaimed_record['token']
        return '{base_url}user/{uid}/{project_id}/claim/?token={token}'\
                    .format(**locals())

    def set_password(self, raw_password):
        """Set the password for this user to the hash of ``raw_password``."""
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Return a boolean of whether ``raw_password`` was correct."""
        if not self.password or not raw_password:
            return False
        return check_password_hash(self.password, raw_password)

    @property
    def csl_given_name(self):
        parts = [self.given_name]
        if self.middle_names:
            parts.extend(each[0] for each in re.split(r'\s+', self.middle_names))
        return ' '.join(parts)

    @property
    def csl_name(self):
        return {
            'family': self.family_name,
            'given': self.csl_given_name,
        }

    # TODO: This should not be on the User object.
    def change_password(self, raw_old_password, raw_new_password, raw_confirm_password):
        """Change the password for this user to the hash of ``raw_new_password``."""
        raw_old_password = (raw_old_password or '').strip()
        raw_new_password = (raw_new_password or '').strip()
        raw_confirm_password = (raw_confirm_password or '').strip()

        issues = []
        if not self.check_password(raw_old_password):
            issues.append('Old password is invalid')
        elif raw_old_password == raw_new_password:
            issues.append('Password cannot be the same')

        if not raw_old_password or not raw_new_password or not raw_confirm_password:
            issues.append('Passwords cannot be blank')
        elif len(raw_new_password) < 6:
            issues.append('Password should be at least six characters')
        elif len(raw_new_password) > 256:
            issues.append('Password should not be longer than 256 characters')

        if raw_new_password != raw_confirm_password:
            issues.append('Password does not match the confirmation')

        if issues:
            raise ChangePasswordError(issues)
        self.set_password(raw_new_password)

    def _set_email_token_expiration(self, token, expiration=None):
        """Set the expiration date for given email token.

        :param str token: The email token to set the expiration for.
        :param datetime expiration: Datetime at which to expire the token. If ``None``, the
            token will expire after ``settings.EMAIL_TOKEN_EXPIRATION`` hours. This is only
            used for testing purposes.
        """
        expiration = expiration or (dt.datetime.utcnow() + dt.timedelta(hours=settings.EMAIL_TOKEN_EXPIRATION))
        self.email_verifications[token]['expiration'] = expiration
        return expiration

    def add_unconfirmed_email(self, email, expiration=None):
        """Add an email verification token for a given email."""

        # TODO: This is technically not compliant with RFC 822, which requires
        #       that case be preserved in the "local-part" of an address. From
        #       a practical standpoint, the vast majority of email servers do
        #       not preserve case.
        #       ref: https://tools.ietf.org/html/rfc822#section-6
        email = email.lower().strip()

        if email in self.emails:
            raise ValueError("Email already confirmed to this user.")

        validate_email(email)

        # If the unconfirmed email is already present, refresh the token
        if email in self.unconfirmed_emails:
            self.remove_unconfirmed_email(email)

        token = generate_confirm_token()

        # handle when email_verifications is None
        if not self.email_verifications:
            self.email_verifications = {}

        self.email_verifications[token] = {'email': email}
        self._set_email_token_expiration(token, expiration=expiration)
        return token

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
        if email in self.emails:
            self.emails.remove(email)
            signals.user_email_removed.send(self, email=email)

    @signals.user_email_removed.connect
    def _send_email_removal_confirmations(self, email):
        mails.send_mail(to_addr=self.username,
                        mail=mails.REMOVED_EMAIL,
                        user=self,
                        removed_email=email)
        mails.send_mail(to_addr=email,
                        mail=mails.REMOVED_EMAIL,
                        user=self,
                        removed_email=email)

    def get_confirmation_token(self, email, force=False):
        """Return the confirmation token for a given email.

        :param str email: Email to get the token for.
        :param bool force: If an expired token exists for the given email, generate a new
            token and return that token.

        :raises: ExpiredTokenError if trying to access a token that is expired and force=False.
        :raises: KeyError if there no token for the email.
        """
        # TODO: Refactor "force" flag into User.get_or_add_confirmation_token
        for token, info in self.email_verifications.items():
            if info['email'].lower() == email.lower():
                # Old records will not have an expiration key. If it's missing,
                # assume the token is expired
                expiration = info.get('expiration')
                if not expiration or (expiration and expiration < dt.datetime.utcnow()):
                    if not force:
                        raise ExpiredTokenError('Token for email "{0}" is expired'.format(email))
                    else:
                        new_token = self.add_unconfirmed_email(email)
                        self.save()
                        return new_token
                return token
        raise KeyError('No confirmation token for email "{0}"'.format(email))

    def get_confirmation_url(self, email, external=True, force=False):
        """Return the confirmation url for a given email.

        :raises: ExpiredTokenError if trying to access a token that is expired.
        :raises: KeyError if there is no token for the email.
        """
        base = settings.DOMAIN if external else '/'
        token = self.get_confirmation_token(email, force=force)
        return "{0}confirm/{1}/{2}/".format(base, self._primary_key, token)

    def _get_unconfirmed_email_for_token(self, token):
        """Return whether or not a confirmation token is valid for this user.
        :rtype: bool
        """
        if token not in self.email_verifications:
            raise exceptions.InvalidTokenError()

        verification = self.email_verifications[token]
        # Not all tokens are guaranteed to have expiration dates
        if (
            'expiration' in verification and
            verification['expiration'] < dt.datetime.utcnow()
        ):
            raise exceptions.ExpiredTokenError()

        return verification['email']

    def verify_claim_token(self, token, project_id):
        """Return whether or not a claim token is valid for this user for
        a given node which they were added as a unregistered contributor for.
        """
        try:
            record = self.get_unclaimed_record(project_id)
        except ValueError:  # No unclaimed record for given pid
            return False
        return record['token'] == token

    def confirm_email(self, token, merge=False):
        """Confirm the email address associated with the token"""
        email = self._get_unconfirmed_email_for_token(token)

        # If this email is confirmed on another account, abort
        try:
            user_to_merge = User.find_one(Q('emails', 'iexact', email))
        except NoResultsFound:
            user_to_merge = None

        if user_to_merge and merge:
            self.merge_user(user_to_merge)
        elif user_to_merge:
            raise exceptions.MergeConfirmedRequiredError(
                'Merge requires confirmation',
                user=self,
                user_to_merge=user_to_merge,
            )

        # If another user has this email as its username, get it
        try:
            unregistered_user = User.find_one(Q('username', 'eq', email) &
                                              Q('_id', 'ne', self._id))
        except NoResultsFound:
            unregistered_user = None

        if unregistered_user:
            self.merge_user(unregistered_user)
            self.save()
            unregistered_user.username = None

        if email not in self.emails:
            self.emails.append(email)

        # Complete registration if primary email
        if email.lower() == self.username.lower():
            self.register(self.username)
            self.date_confirmed = dt.datetime.utcnow()
        # Revoke token
        del self.email_verifications[token]

        # TODO: We can't assume that all unclaimed records are now claimed.
        # Clear unclaimed records, so user's name shows up correctly on
        # all projects
        self.unclaimed_records = {}
        self.save()

        self.update_search_nodes()

        return True

    @property
    def unconfirmed_emails(self):
        # Handle when email_verifications field is None
        email_verifications = self.email_verifications or {}
        return [
            each['email']
            for each
            in email_verifications.values()
        ]

    def update_search_nodes(self):
        """Call `update_search` on all nodes on which the user is a
        contributor. Needed to add self to contributor lists in search upon
        registration or claiming.

        """
        for node in self.node__contributed:
            node.update_search()

    def update_search_nodes_contributors(self):
        """
        Bulk update contributor name on all nodes on which the user is
        a contributor.
        :return:
        """
        from website.search import search
        search.update_contributors(self.visible_contributor_to)

    @property
    def is_confirmed(self):
        return bool(self.date_confirmed)

    @property
    def social_links(self):
        return {
            key: self.SOCIAL_FIELDS[key].format(val)
            for key, val in self.social.items()
            if val and
            self.SOCIAL_FIELDS.get(key)
        }

    @property
    def biblio_name(self):
        given_names = self.given_name + ' ' + self.middle_names
        surname = self.family_name
        if surname != given_names:
            initials = [
                name[0].upper() + '.'
                for name in given_names.split(' ')
                if name and re.search(r'\w', name[0], re.I)
            ]
            return u'{0}, {1}'.format(surname, ' '.join(initials))
        return surname

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
    def url(self):
        return '/{}/'.format(self._primary_key)

    @property
    def api_url(self):
        return '/api/v1/profile/{0}/'.format(self._primary_key)

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    @property
    def deep_url(self):
        return '/profile/{}/'.format(self._primary_key)

    @property
    def gravatar_url(self):
        return filters.gravatar(
            self,
            use_ssl=True,
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        )

    def get_activity_points(self, db=None):
        db = db or framework.mongo.database
        return analytics.get_total_activity_count(self._primary_key, db=db)

    @property
    def is_disabled(self):
        """Whether or not this account has been disabled.

        Abstracts ``User.date_disabled``.

        :return: bool
        """
        return self.date_disabled is not None

    @is_disabled.setter
    def is_disabled(self, val):
        """Set whether or not this account has been disabled."""
        if val:
            self.date_disabled = dt.datetime.utcnow()
        else:
            self.date_disabled = None

    @property
    def is_merged(self):
        '''Whether or not this account has been merged into another account.
        '''
        return self.merged_by is not None

    @property
    def profile_url(self):
        return '/{}/'.format(self._id)

    @property
    def contributor_to(self):
        return (
            node for node in self.node__contributed
            if not (
                node.is_deleted
                or node.is_dashboard
            )
        )

    @property
    def visible_contributor_to(self):
        return (
            node for node in self.contributor_to
            if self._id in node.visible_contributor_ids
        )

    def get_summary(self, formatter='long'):
        return {
            'user_fullname': self.fullname,
            'user_profile_url': self.profile_url,
            'user_display_name': name_formatters[formatter](self),
            'user_is_claimed': self.is_claimed
        }

    def save(self, *args, **kwargs):
        # TODO: Update mailchimp subscription on username change
        # Avoid circular import
        from framework.analytics import tasks as piwik_tasks
        self.username = self.username.lower().strip() if self.username else None
        ret = super(User, self).save(*args, **kwargs)
        if self.SEARCH_UPDATE_FIELDS.intersection(ret) and self.is_confirmed:
            self.update_search()
            self.update_search_nodes_contributors()
        if settings.PIWIK_HOST and not self.piwik_token:
            piwik_tasks.update_user(self._id)
        return ret

    def update_search(self):
        from website import search
        try:
            search.search.update_user(self)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    @classmethod
    def find_by_email(cls, email):
        try:
            user = cls.find_one(
                Q('emails', 'eq', email)
            )
            return [user]
        except:
            return []

    def serialize(self, anonymous=False):
        return {
            'id': utils.privacy_info_handle(self._primary_key, anonymous),
            'fullname': utils.privacy_info_handle(self.fullname, anonymous, name=True),
            'registered': self.is_registered,
            'url': utils.privacy_info_handle(self.url, anonymous),
            'api_url': utils.privacy_info_handle(self.api_url, anonymous),
        }

    ###### OSF-Specific methods ######

    def watch(self, watch_config):
        """Watch a node by adding its WatchConfig to this user's ``watched``
        list. Raises ``ValueError`` if the node is already watched.

        :param watch_config: The WatchConfig to add.
        :param save: Whether to save the user.

        """
        watched_nodes = [each.node for each in self.watched]
        if watch_config.node in watched_nodes:
            raise ValueError('Node is already being watched.')
        watch_config.save()
        self.watched.append(watch_config)
        return None

    def unwatch(self, watch_config):
        """Unwatch a node by removing its WatchConfig from this user's ``watched``
        list. Raises ``ValueError`` if the node is not already being watched.

        :param watch_config: The WatchConfig to remove.
        :param save: Whether to save the user.

        """
        for each in self.watched:
            if watch_config.node._id == each.node._id:
                each.__class__.remove_one(each)
                return None
        raise ValueError('Node not being watched.')

    def is_watching(self, node):
        '''Return whether a not a user is watching a Node.'''
        watched_node_ids = set([config.node._id for config in self.watched])
        return node._id in watched_node_ids

    def get_recent_log_ids(self, since=None):
        '''Return a generator of recent logs' ids.

        :param since: A datetime specifying the oldest time to retrieve logs
        from. If ``None``, defaults to 60 days before today. Must be a tz-aware
        datetime because PyMongo's generation times are tz-aware.

        :rtype: generator of log ids (strings)
        '''
        log_ids = []
        # Default since to 60 days before today if since is None
        # timezone aware utcnow
        utcnow = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
        since_date = since or (utcnow - dt.timedelta(days=60))
        for config in self.watched:
            # Extract the timestamps for each log from the log_id (fast!)
            # The first 4 bytes of Mongo's ObjectId encodes time
            # This prevents having to load each Log Object and access their
            # date fields
            node_log_ids = [log_id for log_id in config.node.logs._to_primary_keys()
                                   if bson.ObjectId(log_id).generation_time > since_date and
                                   log_id not in log_ids]
            # Log ids in reverse chronological order
            log_ids = _merge_into_reversed(log_ids, node_log_ids)
        return (l_id for l_id in log_ids)

    def get_daily_digest_log_ids(self):
        '''Return a generator of log ids generated in the past day
        (starting at UTC 00:00).
        '''
        utcnow = dt.datetime.utcnow()
        midnight = dt.datetime(
            utcnow.year, utcnow.month, utcnow.day,
            0, 0, 0, tzinfo=pytz.utc
        )
        return self.get_recent_log_ids(since=midnight)

    @property
    def can_be_merged(self):
        """The ability of the `merge_user` method to fully merge the user"""
        return all((addon.can_be_merged for addon in self.get_addons()))

    def merge_user(self, user):
        """Merge a registered user into this account. This user will be
        a contributor on any project

        :param user: A User object to be merged.
        """
        # Fail if the other user has conflicts.
        if not user.can_be_merged:
            raise exceptions.MergeConflictError("Users cannot be merged")
        # Move over the other user's attributes
        # TODO: confirm
        for system_tag in user.system_tags:
            if system_tag not in self.system_tags:
                self.system_tags.append(system_tag)

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

        for key, value in user.mailing_lists.iteritems():
            # subscribe to each list if either user was subscribed
            subscription = value or self.mailing_lists.get(key)
            signals.user_merged.send(self, list_name=key, subscription=subscription)

            # clear subscriptions for merged user
            signals.user_merged.send(user, list_name=key, subscription=False)

        for node_id, timestamp in user.comments_viewed_timestamp.iteritems():
            if not self.comments_viewed_timestamp.get(node_id):
                self.comments_viewed_timestamp[node_id] = timestamp
            elif timestamp > self.comments_viewed_timestamp[node_id]:
                self.comments_viewed_timestamp[node_id] = timestamp

        self.emails.extend(user.emails)
        user.emails = []

        for k, v in user.email_verifications.iteritems():
            email_to_confirm = v['email']
            if k not in self.email_verifications and email_to_confirm != user.username:
                self.email_verifications[k] = v
        user.email_verifications = {}

        # FOREIGN FIELDS
        for watched in user.watched:
            if watched not in self.watched:
                self.watched.append(watched)
        user.watched = []

        for account in user.external_accounts:
            if account not in self.external_accounts:
                self.external_accounts.append(account)
        user.external_accounts = []

        # - addons
        # Note: This must occur before the merged user is removed as a
        #       contributor on the nodes, as an event hook is otherwise fired
        #       which removes the credentials.
        for addon in user.get_addons():
            user_settings = self.get_or_add_addon(addon.config.short_name)
            user_settings.merge(addon)
            user_settings.save()

        # - projects where the user was a contributor
        for node in user.node__contributed:
            # Skip dashboard node
            if node.is_dashboard:
                continue
            node.add_contributor(
                contributor=self,
                permissions=node.get_permissions(user),
                visible=node.get_visible(user),
                log=False,
            )
            try:
                node.remove_contributor(
                    contributor=user,
                    auth=Auth(user=self),
                    log=False,
                )
            except ValueError:
                logger.error('Contributor {0} not in list on node {1}'.format(
                    user._id, node._id
                ))
            node.save()

        # - projects where the user was the creator
        for node in user.node__created:
            node.creator = self
            node.save()

        # finalize the merge

        remove_sessions_for_user(user)

        # - username is set to None so the resultant user can set it primary
        #   in the future.
        user.username = None
        user.password = None
        user.verification_key = None
        user.merged_by = self

        user.save()

    def get_projects_in_common(self, other_user, primary_keys=True):
        """Returns either a collection of "shared projects" (projects that both users are contributors for)
        or just their primary keys
        """
        if primary_keys:
            projects_contributed_to = set(self.node__contributed._to_primary_keys())
            return projects_contributed_to.intersection(other_user.node__contributed._to_primary_keys())
        else:
            projects_contributed_to = set(self.node__contributed)
            return projects_contributed_to.intersection(other_user.node__contributed)

    def n_projects_in_common(self, other_user):
        """Returns number of "shared projects" (projects that both users are contributors for)"""
        return len(self.get_projects_in_common(other_user, primary_keys=True))


def _merge_into_reversed(*iterables):
    '''Merge multiple sorted inputs into a single output in reverse order.
    '''
    return sorted(itertools.chain(*iterables), reverse=True)
