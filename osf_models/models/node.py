import urlparse

from django.core.exceptions import ValidationError
from django.db import models

from modularodm import Q

from osf_models.models.contributor import Contributor
from osf_models.models.tag import Tag
from osf_models.models.user import User
from osf_models.models.validators import validate_title
from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField
from .base import BaseModel, GuidMixin

from website.util import api_v2_url

from website import settings


class Node(GuidMixin, BaseModel):
    # TODO: Alphabetize properties because sanity
    CATEGORY_MAP = dict((
        ('analysis', 'Analysis'),
        ('communication', 'Communication'),
        ('data', 'Data'),
        ('hypothesis', 'Hypothesis'),
        ('instrumentation', 'Instrumentation'),
        ('methods and measures', 'Methods and Measures'),
        ('procedure', 'Procedure'),
        ('project', 'Project'),
        ('software', 'Software'),
        ('other', 'Other'),
        ('', 'Uncategorized')
    ))

    @classmethod
    def find_one(cls, query=None, allow_institution=False, **kwargs):
        if not allow_institution:
            query = (query & Q('institution_id', 'eq', None)) if query else Q('institution_id', 'eq', None)
        return super(Node, cls).find_one(query, **kwargs)

    date_created = models.DateTimeField(null=False) # auto_now_add=True)
    date_modified = models.DateTimeField(null=True, db_index=True) # auto_now=True)

    is_public = models.BooleanField(default=False, db_index=True)

    # permissions = Permissions are now on contributors
    # visible_contributor_ids =
    @property
    def visible_contributor_ids(self):
        return self.contributor_set.filter(visible=True)

    is_bookmark_collection = models.BooleanField(default=False, db_index=True)
    is_collection = models.BooleanField(default=False, db_index=True)

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_date = models.DateTimeField(null=True)

    is_registration = models.BooleanField(default=False, db_index=True)
    registered_date = models.DateTimeField(db_index=True, null=True)
    registered_user = models.ForeignKey(User, related_name='related_to', on_delete=models.SET_NULL, null=True)

    # registered_schema = models.ManyToManyField(Metaschema)

    registered_meta = DatetimeAwareJSONField(default={})
    # registration_approval = models.ForeignKey(RegistrationApproval)
    # retraction = models.ForeignKey(Retraction)
    # embargo = models.ForeignKey(Embargo)

    is_fork = models.BooleanField(default=False, db_index=True)
    forked_date = models.DateTimeField(db_index=True, null=True)

    title = models.TextField(validators=[validate_title]) # this should be a charfield but data from mongo didn't fit in 255
    description = models.TextField()
    category = models.CharField(max_length=255, choices=CATEGORY_MAP.items(), default=CATEGORY_MAP[''])
    # node_license = models.ForeignKey(NodeLicenseRecord)

    public_comments = models.BooleanField(default=True)

    wiki_pages_current = DatetimeAwareJSONField()
    wiki_pages_versions = DatetimeAwareJSONField()
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = DatetimeAwareJSONField()
    file_guid_to_share_uuids = DatetimeAwareJSONField()

    creator = models.ForeignKey(User, db_index=True, related_name='created', on_delete=models.SET_NULL, null=True)
    contributors = models.ManyToManyField(User, through=Contributor, related_name='contributed_to')
    # TODO why is this here if it's empty
    users_watching_node = models.ManyToManyField(User, related_name='watching')

    # logs = Logs have a reverse relation to nodes
    tags = models.ManyToManyField(Tag, related_name='tagged')

    # Tags for internal use
    system_tags = models.ManyToManyField(Tag, related_name='tagged_by_system')

    nodes = models.ManyToManyField('self', related_name='children')
    forked_from = models.ForeignKey('self', related_name='forks', on_delete=models.SET_NULL, null=True)
    registered_from = models.ForeignKey('self', related_name='registrations', on_delete=models.SET_NULL, null=True)
    root = models.ForeignKey('self', related_name='absolute_parent', on_delete=models.SET_NULL, null=True)
    parent_node = models.ForeignKey('self', related_name='parent', on_delete=models.SET_NULL, null=True)

    # The node (if any) used as a template for this node's creation
    template_node = models.ForeignKey('self', related_name='templated_from', on_delete=models.SET_NULL, null=True)

    piwik_site_id = models.IntegerField(null=True)

    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    # TODO: Can this be a reference instead of data?
    child_node_subscriptions = DatetimeAwareJSONField()

    # TODO: Sort this out so it's not awful
    institution_id = models.CharField(db_index=True, max_length=255, blank=True)
    institution_domains = DatetimeAwareJSONField(default=None)
    institution_auth_url = models.URLField(blank=True)
    institution_logo_name = models.CharField(max_length=255, blank=True)
    institution_email_domains = DatetimeAwareJSONField(default=None)
    institution_banner_name = models.CharField(max_length=255, blank=True)
    _primary_institution = models.ForeignKey('self', related_name='primary_institution', null=True)
    _affiliated_institutions = models.ManyToManyField('self')

    # alternative_citations = models.ManyToManyField(AlternativeCitation)

    @property
    def comment_level(self):
        if self.public_comments:
            return 'public'
        else:
            return 'private'

    @comment_level.setter
    def comment_level(self, value):
        if value == 'public':
            self.public_comments = True
        elif value == 'private':
            self.public_comments = False
        else:
            raise ValidationError('comment_level must be either `public` or `private`')

    def get_permissions(self, user):
        contrib = user.contributor_set.get(node=self)
        perm = []
        if contrib.admin:
            perm.append('admin')
        if contrib.write:
            perm.append('write')
        if contrib.read:
            perm.append('read')
        return []

    def has_permission(self, user, permission):
        return getattr(user.contributor_set.get(node=self), permission, False)

    @property
    def url(self):
        return '/{}/'.format(self._id)

    @property
    def absolute_url(self):
        if not self.url:
            return None
        return urlparse.urljoin(settings.DOMAIN, self.url)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_api_v2_url(self):
        if self.is_registration:
            path = '/registrations/{}/'.format(self._id)
            return api_v2_url(path)
        if self.is_collection:
            path = '/collections/{}/'.format(self._id)
            return api_v2_url(path)
        path = '/nodes/{}/'.format(self._id)
        return api_v2_url(path)

    def can_view(self, auth):
        if auth and getattr(auth.private_link, 'anonymous', False):
            return self._id in auth.private_link.nodes

        if not auth and not self.is_public:
            return False

        return (
            self.is_public or
            (auth.user and self.has_permission(auth.user, 'read')) or
            auth.private_key in self.private_link_keys_active or
            self.is_admin_parent(auth.user)
        )

    @property
    def is_retracted(self):
        return False

    @property
    def nodes_pointer(self):
        return []
