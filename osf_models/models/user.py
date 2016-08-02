import datetime as dt

from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.postgres import fields
from django.core.validators import validate_email
from django.db import models
from osf_models.exceptions import reraise_django_validation_errors
from osf_models.models.base import BaseModel, GuidMixin
from osf_models.models.tag import Tag
from osf_models.utils import security
from osf_models.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf_models.utils.names import impute_names


# Hide implementation of token generation
def generate_confirm_token():
    return security.random_string(30)


def get_default_mailing_lists():
    return {'Open Science Framework Help': True}


class OSFUserManager(BaseUserManager):
    def create_user(self, username, password=None):
        if not username:
            raise ValueError('Users must have a username')

        user = self.model(
            username=self.normalize_email(username),
            is_active=True,
            date_registered=dt.datetime.today()
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        user = self.create_user(username, password=password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user


class OSFUser(GuidMixin, BaseModel, AbstractBaseUser, PermissionsMixin):
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

    # TODO: Add SEARCH_UPDATE_NODE_FIELDS, for fields that should trigger a
    #   search update for all nodes to which the user is a contributor.

    SOCIAL_FIELDS = {
        'orcid': u'http://orcid.org/{}',
        'github': u'http://github.com/{}',
        'scholar': u'http://scholar.google.com/citations?user={}',
        'twitter': u'http://twitter.com/{}',
        'profileWebsites': [],
        'linkedIn': u'https://www.linkedin.com/{}',
        'impactStory': u'https://impactstory.org/{}',
        'researcherId': u'http://researcherid.com/rid/{}',
        'researchGate': u'https://researchgate.net/profile/{}',
        'academiaInstitution': u'https://{}',
        'academiaProfileID': u'.academia.edu/{}',
        'baiduScholar': u'http://xueshu.baidu.com/scholarID/{}'
    }

    # The primary email address for the account.
    # This value is unique, but multiple "None" records exist for:
    #   * unregistered contributors where an email address was not provided.
    # TODO: Update mailchimp subscription on username change in user.save()
    username = models.CharField(max_length=255, db_index=True, unique=True)

    # Hashed. Use `User.set_password` and `User.check_password`
    # password = models.CharField(max_length=255)

    fullname = models.CharField(max_length=255, blank=True)

    # user has taken action to register the account
    is_registered = models.BooleanField(db_index=True, default=False)

    # user has claimed the account
    # TODO: This should be retired - it always reflects is_registered.
    #   While a few entries exist where this is not the case, they appear to be
    #   the result of a bug, as they were all created over a small time span.
    is_claimed = models.BooleanField(default=False, db_index=True)

    # a list of strings - for internal use
    system_tags = models.ManyToManyField(Tag)

    # security emails that have been sent
    # TODO: This should be removed and/or merged with system_tags
    security_messages = DateTimeAwareJSONField(default={}, blank=True)
    # Format: {
    #   <message label>: <datetime>
    #   ...
    # }

    # user was invited (as opposed to registered unprompted)
    is_invited = models.BooleanField(default=False, db_index=True)

    # Per-project unclaimed user data:
    # TODO: add validation
    unclaimed_records = DateTimeAwareJSONField(default={}, blank=True)
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
    contributor_added_email_records = DateTimeAwareJSONField(default={}, blank=True)

    # The user into which this account was merged
    merged_by = models.ForeignKey('self', null=True, blank=True)

    # verification key used for resetting password
    verification_key = models.CharField(max_length=255, null=True, blank=True)

    # confirmed emails
    #   emails should be stripped of whitespace and lower-cased before appending
    # TODO: Add validator to ensure an email address only exists once across
    # TODO: Change to m2m field per @sloria
    # all User's email lists
    emails = fields.ArrayField(models.CharField(max_length=255), default=list, blank=True)

    # email verification tokens
    #   see also ``unconfirmed_emails``
    email_verifications = DateTimeAwareJSONField(default={}, blank=True)
    # Format: {
    #   <token> : {'email': <email address>,
    #              'expiration': <datetime>}
    # }

    # TODO remove this field once migration (scripts/migration/migrate_mailing_lists_to_mailchimp_fields.py)
    # has been run. This field is deprecated and replaced with mailchimp_mailing_lists
    mailing_lists = DateTimeAwareJSONField(default={}, blank=True)

    # email lists to which the user has chosen a subscription setting
    mailchimp_mailing_lists = DateTimeAwareJSONField(default={}, blank=True)
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # email lists to which the user has chosen a subscription setting, being sent from osf, rather than mailchimp
    osf_mailing_lists = DateTimeAwareJSONField(
        default=get_default_mailing_lists)
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # the date this user was registered
    date_registered = models.DateTimeField(db_index=True
                                           )  #, auto_now_add=True)

    # watched nodes are stored via a list of WatchConfigs
    # watched = fields.ForeignField("WatchConfig", list=True)
    # watched = models.ManyToManyField(WatchConfig)

    # list of collaborators that this user recently added to nodes as a contributor
    # recently_added = fields.ForeignField("user", list=True)
    recently_added = models.ManyToManyField('self')

    # Attached external accounts (OAuth)
    # external_accounts = fields.ForeignField("externalaccount", list=True)
    # external_accounts = models.ManyToManyField(ExternalAccount)

    # CSL names
    given_name = models.CharField(max_length=255, blank=True)
    middle_names = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    suffix = models.CharField(max_length=255, blank=True)

    # Employment history
    # jobs = fields.DictionaryField(list=True, validate=validate_history_item)
    # TODO: Add validation
    jobs = DateTimeAwareJSONField(default={}, blank=True)
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
    # schools = fields.DictionaryField(list=True, validate=validate_history_item)
    # TODO: Add validation
    schools = DateTimeAwareJSONField(default={}, blank=True)
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
    # social = fields.DictionaryField(validate=validate_social)
    # TODO: Add validation
    social = DateTimeAwareJSONField(default={}, blank=True)
    # Format: {
    #     'profileWebsites': <list of profile websites>
    #     'twitter': <twitter id>,
    # }

    # hashed password used to authenticate to Piwik
    piwik_token = models.CharField(max_length=255, blank=True)

    # date the user last sent a request
    date_last_login = models.DateTimeField(null=True, blank=True)

    # date the user first successfully confirmed an email address
    date_confirmed = models.DateTimeField(db_index=True, null=True, blank=True)

    # When the user was disabled.
    date_disabled = models.DateTimeField(db_index=True, null=True, blank=True)

    # when comments were last viewed
    comments_viewed_timestamp = DateTimeAwareJSONField(default={}, blank=True)
    # Format: {
    #   'Comment.root_target._id': 'timestamp',
    #   ...
    # }

    # timezone for user's locale (e.g. 'America/New_York')
    timezone = models.CharField(default='Etc/UTC', max_length=255)

    # user language and locale data (e.g. 'en_US')
    locale = models.CharField(max_length=255, default='en_US')

    # whether the user has requested to deactivate their account
    requested_deactivation = models.BooleanField(default=False)

    _affiliated_institutions = models.ManyToManyField('Institution')

    notifications_configured = DateTimeAwareJSONField(default={}, blank=True)

    objects = OSFUserManager()

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    def __unicode__(self):
        return u'{}: {} {}'.format(self.username, self.given_name, self.family_name)

    @property
    def url(self):
        return '/{}/'.format(self._id)

    @property
    def api_url(self):
        return '/api/v1/profile/{}/'.format(self._id)

    @property
    def is_disabled(self):
        return self.date_disabled is not None

    @is_disabled.setter
    def is_disabled(self, val):
        """Set whether or not this account has been disabled."""
        if val and not self.date_disabled:
            self.date_disabled = dt.datetime.utcnow()
        elif val is False:
            self.date_disabled = None

    @property
    def is_confirmed(self):
        return bool(self.date_confirmed)

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
    def email(self):
        return self.username

    def is_authenticated(self):  # Needed for django compat
        return True

    def is_anonymous(self):
        return False

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

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        django_obj = super(OSFUser, cls).migrate_from_modm(modm_obj)
        if django_obj.password == '' or django_obj.password is None:
            # password is blank=False, null=False
            # make them have a password
            django_obj.set_unusable_password()
        else:
            # django thinks bcrypt should start with bcrypt...
            django_obj.password = 'bcrypt${}'.format(django_obj.password)
        return django_obj

    # Legacy methods

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
    def create_unconfirmed(cls, username, password, fullname, do_confirm=True,
                           campaign=None):
        """Create a new user who has begun registration but needs to verify
        their primary email address (username).
        """
        user = cls.create(username, password, fullname)
        user.add_unconfirmed_email(username)
        user.is_registered = False
        if campaign:
            # needed to prevent cirular import
            from framework.auth.campaigns import system_tag_for_campaign  # skipci
            user.system_tags.append(system_tag_for_campaign(campaign))
        return user

    def update_guessed_names(self):
        """Updates the CSL name fields inferred from the the full name.
        """
        parsed = impute_names(self.fullname)
        self.given_name = parsed['given']
        self.middle_names = parsed['middle']
        self.family_name = parsed['family']
        self.suffix = parsed['suffix']


    def add_unconfirmed_email(self, email, expiration=None):
        """Add an email verification token for a given email."""

        # TODO: This is technically not compliant with RFC 822, which requires
        #       that case be preserved in the "local-part" of an address. From
        #       a practical standpoint, the vast majority of email servers do
        #       not preserve case.
        #       ref: https://tools.ietf.org/html/rfc822#section-6
        email = email.lower().strip()

        if email in self.emails:
            raise ValueError('Email already confirmed to this user.')

        with reraise_django_validation_errors():
            validate_email(email)

        # If the unconfirmed email is already present, refresh the token
        if email in self.unconfirmed_emails:
            self.remove_unconfirmed_email(email)

        token = generate_confirm_token()

        # handle when email_verifications is None
        if not self.email_verifications:
            self.email_verifications = {}

        # confirmed used to check if link has been clicked
        self.email_verifications[token] = {'email': email,
                                           'confirmed': False}
        self._set_email_token_expiration(token, expiration=expiration)
        return token

    def _set_email_token_expiration(self, token, expiration=None):
        """Set the expiration date for given email token.

        :param str token: The email token to set the expiration for.
        :param datetime expiration: Datetime at which to expire the token. If ``None``, the
            token will expire after ``settings.EMAIL_TOKEN_EXPIRATION`` hours. This is only
            used for testing purposes.
        """
        settings = apps.get_app_config('osf_models')
        expiration = expiration or (dt.datetime.utcnow() + dt.timedelta(hours=settings.email_token_expiration))
        self.email_verifications[token]['expiration'] = expiration
        return expiration
