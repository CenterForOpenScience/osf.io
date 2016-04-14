from django.core.exceptions import ValidationError
from django.db import models

from osf_models.models.permissions import Permissions
from osf_models.models.tag import Tag
from osf_models.models.user import User
from osf_models.models.validators import validate_title
from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField
from .base import BaseModel, GuidMixin


class Node(GuidMixin, BaseModel):
    CATEGORY_MAP = (
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
    )

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    is_public = models.BooleanField(default=False, db_index=True)

    # permissions = Permissions are now on contributors
    # visible_contributor_ids =

    is_bookmark_collection = models.BooleanField(default=False, db_index=True)
    is_collection = models.BooleanField(default=False, db_index=True)

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_date = models.DateTimeField()

    is_registration = models.BooleanField(default=False, db_index=True)
    registered_date = models.DateTimeField(db_index=True)
    registered_user = models.ForeignKey(User, related_name='related_to', on_delete=models.SET_NULL, null=True)

    # registered_schema = models.ManyToManyField(Metaschema)

    registered_meta = DatetimeAwareJSONField()
    # registration_approval = models.ForeignKey(RegistrationApproval)
    # retraction = models.ForeignKey(Retraction)
    # embargo = models.ForeignKey(Embargo)

    is_fork = models.BooleanField(default=False, db_index=True)
    forked_date = models.DateTimeField(db_index=True)

    title = models.CharField(validators=[validate_title], max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=255, choices=CATEGORY_MAP, default=CATEGORY_MAP[-1])
    # node_license = models.ForeignKey(NodeLicenseRecord)

    public_comments = models.BooleanField(default=True)

    wiki_pages_current = DatetimeAwareJSONField()
    wiki_pages_versions = DatetimeAwareJSONField()
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = DatetimeAwareJSONField()
    file_guid_to_share_uuids = DatetimeAwareJSONField()

    creator = models.ForeignKey(User, db_index=True, related_name='created', on_delete=models.SET_NULL, null=True)
    contributors = models.ManyToManyField(User, through=Permissions, related_name='contributed_to')
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

    piwik_site_id = models.IntegerField()

    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    # TODO: Can this be a reference instead of data?
    child_node_subscriptions = DatetimeAwareJSONField()

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

