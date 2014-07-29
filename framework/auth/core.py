# -*- coding: utf-8 -*-
import re
import itertools
import logging
import urlparse
import datetime as dt

import pytz
import bson

from modularodm.validators import URLValidator
from modularodm.exceptions import ValidationValueError

from framework import session
from framework.analytics import piwik
from framework.bcrypt import generate_password_hash, check_password_hash
from framework import fields, Q, analytics
from framework.guid.model import GuidStoredObject
from framework.addons import AddonModelMixin
from framework.auth import utils
from framework.exceptions import PermissionsError

from website import settings, filters, security


name_formatters = {
   'long': lambda user: user.fullname,
   'surname': lambda user: user.family_name if user.family_name else user.fullname,
   'initials': lambda user: u'{surname}, {initial}.'.format(
       surname=user.family_name,
       initial=user.given_name_initial
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
    string_required(item.get('institution'))
    start = item.get('start')
    end = item.get('end')
    if start and end and end < start:
        raise ValidationValueError('End date must be later than start date.')


validate_url = URLValidator()
def validate_personal_site(value):
    if value:
       validate_url(value)


def validate_social(value):
    validate_personal_site(value.get('personal_site'))


def get_current_username():
    return session.data.get('auth_user_username')


def get_current_user_id():
    return session.data.get('auth_user_id')


def get_current_user():
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return User.load(uid)


# TODO(sloria): This belongs in website.project
def get_current_node():
    from website.models import Node
    nid = session.data.get('auth_node_id')
    if nid:
        return Node.load(nid)


def get_api_key():
    # Hack: Avoid circular import
    from website.project.model import ApiKey
    api_key = session.data.get('auth_api_key')
    return ApiKey.load(api_key)


# TODO: This should be a class method of User
def get_user(id=None, username=None, password=None, verification_key=None):
    # tag: database
    query_list = []
    if id:
        query_list.append(Q('_id', 'eq', id))
    if username:
        username = username.strip().lower()
        query_list.append(Q('username', 'eq', username))
    if password:
        password = password.strip()
        try:
            query = query_list[0]
            for query_part in query_list[1:]:
                query = query & query_part
            user = User.find_one(query)
        except Exception as err:
            logging.error(err)
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
        logging.error(err)
        return None


class Auth(object):

    def __init__(self, user=None, api_key=None, api_node=None,
                 private_key=None):
        self.user = user
        self.api_key = api_key
        self.api_node = api_node
        self.private_key = private_key

    @property
    def logged_in(self):
        return self.user is not None

    @classmethod
    def from_kwargs(cls, request_args, kwargs):
        user = request_args.get('user') or kwargs.get('user') or get_current_user()
        api_key = request_args.get('api_key') or kwargs.get('api_key') or get_api_key()
        api_node = request_args.get('api_node') or kwargs.get('api_node') or get_current_node()
        private_key = request_args.get('view_only')
        return cls(
            user=user,
            api_key=api_key,
            api_node=api_node,
            private_key=private_key,
        )


class User(GuidStoredObject, AddonModelMixin):

    redirect_mode = 'proxy'

    # Node fields that trigger an update to the search engine on save
    SEARCH_UPDATE_FIELDS = {
        'fullname',
        'merged_by',
    }

    _id = fields.StringField(primary=True)

    # NOTE: In the OSF, username is an email
    # May be None for unregistered contributors
    username = fields.StringField(required=False, unique=True, index=True)
    password = fields.StringField()
    fullname = fields.StringField(required=True, validate=string_required)
    is_registered = fields.BooleanField()
    is_claimed = fields.BooleanField()  # TODO: Unused. Remove me?
    private_links = fields.ForeignField('privatelink', list=True)

    # Tags for internal use
    system_tags = fields.StringField(list=True)

    # Per-project unclaimed user data:
    # Format: {
    #   <project_id>: {
    #       'name': <name that referrer provided>,
    #       'referrer_id': <user ID of referrer>,
    #       'token': <token used for verification urls>,
    #       'email': <email the referrer provided or None>,
    #       'last_sent': <timestamp of last email sent to referrer or None>
    #   }
    #   ...
    # }
    # TODO: add validation
    unclaimed_records = fields.DictionaryField(required=False)
    # The user who merged this account
    merged_by = fields.ForeignField('user', default=None, backref="merged")
    #: Verification key used for resetting password
    verification_key = fields.StringField()
    emails = fields.StringField(list=True)
    # Email verification tokens
    # Format: {
    #   <token> : {'email': <email address>}
    # }
    # TODO: add timestamp to allow for timed expiration?
    email_verifications = fields.DictionaryField()
    aka = fields.StringField(list=True)
    date_registered = fields.DateTimeField(auto_now_add=dt.datetime.utcnow)
    # Watched nodes are stored via a list of WatchConfigs
    watched = fields.ForeignField("WatchConfig", list=True, backref="watched")

    # Recently added contributors stored via a list of users
    recently_added = fields.ForeignField("user", list=True, backref="recently_added")

    # CSL names
    given_name = fields.StringField()
    middle_names = fields.StringField()
    family_name = fields.StringField()
    suffix = fields.StringField()

    # Employment history
    # Format: {
    #     'position': <position or job title>,
    #     'institution': <institution or organization>,
    #     'department': <department>,
    #     'location': <location>,
    #     'start': <start date>,
    #     'end': <end date>,
    # }
    jobs = fields.DictionaryField(list=True, validate=validate_history_item)

    # Educational history
    # Format: {
    #     'degree': <position or job title>,
    #     'institution': <institution or organization>,
    #     'department': <department>,
    #     'location': <location>,
    #     'start': <start date>,
    #     'end': <end date>,
    # }
    schools = fields.DictionaryField(list=True, validate=validate_history_item)

    # Social links
    # Format: {
    #     'personal': <personal site>,
    #     'twitter': <twitter id>,
    # }
    social = fields.DictionaryField(validate=validate_social)

    api_keys = fields.ForeignField('apikey', list=True, backref='keyed')

    piwik_token = fields.StringField()

    date_last_login = fields.DateTimeField()

    date_confirmed = fields.DateTimeField()

    _meta = {'optimistic' : True}

    def __repr__(self):
        return '<User {0!r}>'.format(self.username)

    @property
    def private_link_keys(self):
        return [x.key for x in self.private_links]

    @classmethod
    def create_unregistered(cls, fullname, email=None):
        """Creates a new unregistered user.

        :raises: DuplicateEmailError if a user with the given email address
            is already in the database.
        """
        user = cls(
            username=email,
            fullname=fullname,
        )
        user.update_guessed_names()
        if email:
            user.emails.append(email)
        user.is_registered = False
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
        user.add_email_verification(username)
        user.is_registered = False
        return user

    @classmethod
    def create_confirmed(cls, username, password, fullname):
        user = cls.create(username, password, fullname)
        user.is_registered = True
        user.is_claimed = True
        user.date_confirmed = user.date_registered
        return user

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

    def is_active(self):
        """Returns True if the user is active. The user must have activated
        their account, must not be deleted, suspended, etc.
        """
        return (self.is_registered and
                self.password is not None and
                not self.is_merged and
                self.is_confirmed())

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
        '''Set the password for this user to the hash of ``raw_password``.'''
        self.password = generate_password_hash(raw_password)
        return None

    def check_password(self, raw_password):
        '''Return a boolean of whether ``raw_password`` was correct.'''
        if not self.password or not raw_password:
            return False
        return check_password_hash(self.password, raw_password)

    def add_email_verification(self, email):
        """Add an email verification token for a given email."""
        token = generate_confirm_token()
        self.email_verifications[token] = {'email': email}
        return token

    def get_confirmation_token(self, email):
        """Return the confirmation token for a given email.

        :raises: KeyError if there no token for the email
        """
        for token, info in self.email_verifications.items():
            if info['email'] == email:
                return token
        raise KeyError('No confirmation token for email {0!r}'.format(email))

    def get_confirmation_url(self, email, external=True):
        """Return the confirmation url for a given email.

        :raises: KeyError if there is no token for the email.
        """
        base = settings.DOMAIN if external else '/'
        token = self.get_confirmation_token(email)
        return "{0}confirm/{1}/{2}/".format(base, self._primary_key, token)

    def verify_confirmation_token(self, token):
        """Return whether or not a confirmation token is valid for this user.
        """
        return token in self.email_verifications.keys()

    def verify_claim_token(self, token, project_id):
        """Return whether or not a claim token is valid for this user for
        a given node which they were added as a unregistered contributor for.
        """
        try:
            record = self.get_unclaimed_record(project_id)
        except ValueError:  # No unclaimed record for given pid
            return False
        return record['token'] == token

    def confirm_email(self, token):
        if self.verify_confirmation_token(token):
            email = self.email_verifications[token]['email']
            self.emails.append(email)
            # Complete registration if primary email
            if email == self.username:
                self.register(self.username)
                self.date_confirmed = dt.datetime.utcnow()
            # Revoke token
            del self.email_verifications[token]
            self.save()
            # Note: We must manually update search here because the fullname
            # field has not changed
            self.update_search()
            self.update_search_nodes()
            return True
        else:
            return False

    def update_search_nodes(self):
        """Call `update_search` on all nodes on which the user is a
        contributor. Needed to add self to contributor lists in search upon
        registration or claiming.

        """
        for node in self.node__contributed:
            node.update_search()

    def is_confirmed(self):
        return bool(self.date_confirmed)

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

    @property
    def activity_points(self):
        return analytics.get_total_activity_count(self._primary_key)

    @property
    def is_merged(self):
        '''Whether or not this account has been merged into another account.
        '''
        return self.merged_by is not None

    @property
    def profile_url(self):
        return '/{}/'.format(self._id)

    def get_summary(self, formatter='long'):
        return {
            'user_fullname': self.fullname,
            'user_profile_url': self.profile_url,
            'user_display_name': name_formatters[formatter](self),
            'user_is_claimed': self.is_claimed
        }

    def save(self, *args, **kwargs):
        self.username = self.username.lower().strip() if self.username else None
        rv = super(User, self).save(*args, **kwargs)
        if self.SEARCH_UPDATE_FIELDS.intersection(rv):
            self.update_search()
        if settings.PIWIK_HOST and not self.piwik_token:
            try:
                piwik.create_user(self)
            except (piwik.PiwikException, ValueError):
                logger.error("Piwik user creation failed: " + self._id)
        return rv

    def update_search(self):
        from website.search import search
        search.update_user(self)

    @classmethod
    def find_by_email(cls, email):
        try:
            user = cls.find_one(
                Q('emails', 'eq', email)
            )
            return [user]
        except:
            return []

    def serialize(self):
        return {
            'id': self._primary_key,
            'fullname': self.fullname,
            'registered': self.is_registered,
            'url': self.url,
            'api_url': self.api_url,
        }

    ###### OSF-Specific methods ######

    def watch(self, watch_config, save=False):
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
        if save:
            self.save()
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
                                   if bson.ObjectId(log_id).generation_time > since_date]
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

    def merge_user(self, user, save=False):
        """Merge a registered user into this account. This user will be
        a contributor on any project

        :param user: A User object to be merged.
        """
        # Inherit emails
        self.emails.extend(user.emails)
        # Inherit projects the user was a contributor for
        for node in user.node__contributed:
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
        # Inherits projects the user created
        for node in user.node__created:
            node.creator = self
            node.save()
        user.merged_by = self
        user.save()
        if save:
            self.save()
        return None

    def get_projects_in_common(self, other_user, primary_keys= True):
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
