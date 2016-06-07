import datetime
from .base import BaseModel, GuidMixin
from django.db import models
from .tag import Tag
from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField
from website import settings


def get_default_mailing_lists():
    return {settings.OSF_HELP_LIST: True}


class User(GuidMixin, BaseModel):
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
    username = models.CharField(max_length=255, db_index=True)

    # Hashed. Use `User.set_password` and `User.check_password`
    password = models.CharField(max_length=255)

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
    security_messages = DatetimeAwareJSONField(default={})
    # Format: {
    #   <message label>: <datetime>
    #   ...
    # }

    # user was invited (as opposed to registered unprompted)
    is_invited = models.BooleanField(default=False, db_index=True)

    # Per-project unclaimed user data:
    # TODO: add validation
    unclaimed_records = DatetimeAwareJSONField(default={})
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
    contributor_added_email_records = DatetimeAwareJSONField(default={})

    # The user into which this account was merged
    merged_by = models.ForeignKey('self', null=True)

    # verification key used for resetting password
    verification_key = models.CharField(max_length=255, blank=True, null=True)

    # confirmed emails
    #   emails should be stripped of whitespace and lower-cased before appending
    # TODO: Add validator to ensure an email address only exists once across
    # all User's email lists
    emails = DatetimeAwareJSONField(default={})

    # email verification tokens
    #   see also ``unconfirmed_emails``
    email_verifications = DatetimeAwareJSONField(default={})
    # Format: {
    #   <token> : {'email': <email address>,
    #              'expiration': <datetime>}
    # }

    # TODO remove this field once migration (scripts/migration/migrate_mailing_lists_to_mailchimp_fields.py)
    # has been run. This field is deprecated and replaced with mailchimp_mailing_lists
    mailing_lists = DatetimeAwareJSONField(default={})

    # email lists to which the user has chosen a subscription setting
    mailchimp_mailing_lists = DatetimeAwareJSONField(default={})
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # email lists to which the user has chosen a subscription setting, being sent from osf, rather than mailchimp
    osf_mailing_lists = DatetimeAwareJSONField(
        default=get_default_mailing_lists)
    # Format: {
    #   'list1': True,
    #   'list2: False,
    #    ...
    # }

    # the date this user was registered
    # TODO: consider removal - this can be derived from date_registered
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
    jobs = DatetimeAwareJSONField(default={})
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
    schools = DatetimeAwareJSONField(default={})
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
    social = DatetimeAwareJSONField(default={})
    # Format: {
    #     'profileWebsites': <list of profile websites>
    #     'twitter': <twitter id>,
    # }

    # hashed password used to authenticate to Piwik
    piwik_token = models.CharField(max_length=255, blank=True)

    # date the user last sent a request
    date_last_login = models.DateTimeField(null=True)

    # date the user first successfully confirmed an email address
    date_confirmed = models.DateTimeField(db_index=True, null=True)

    # When the user was disabled.
    date_disabled = models.DateTimeField(db_index=True, null=True)

    # when comments were last viewed
    comments_viewed_timestamp = DatetimeAwareJSONField(default={})
    # Format: {
    #   'Comment.root_target._id': 'timestamp',
    #   ...
    # }

    # timezone for user's locale (e.g. 'America/New_York')
    timezone = models.CharField(default='Etc/UTC', max_length=255)

    # user language and locale data (e.g. 'en_US')
    locale = models.CharField(max_length=255, default='en_US')

    _affiliated_institutions = models.ManyToManyField('Node')

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
            self.date_disabled = datetime.datetime.utcnow()
        elif val is False:
            self.date_disabled = None

    @property
    def is_confirmed(self):
        return bool(self.date_confirmed)

    def is_authenticated(self):  # Needed for django compat
        return True

    def is_anonymous(self):
        return False

    def get_addon_names(self):
        return []
