from django.core.exceptions import ValidationError
from website.util import sanitize

from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField
from .base import BaseModel
from django.db import models

class Node(BaseModel):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    is_public = models.BooleanField(default=False, db_index=True)

    # permissions =
    # visible_contributor_ids =

    is_bookmark_collection = models.BooleanField(default=False, db_index=True)
    is_collection = models.BooleanField(default=False, db_index=True)

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_date = models.DateTimeField()

    is_registration = models.BooleanField(default=False, db_index=True)
    registered_date = models.DateTimeField(db_index=True)
    # registered_user = models.ForeignKey(User)

    # registered_schema = models.ManyToManyField(Metaschema)

    registered_meta = DatetimeAwareJSONField()
    # registration_approval = models.ForeignKey(RegistrationApproval)
    # retraction = models.ForeignKey(Retraction)
    # embargo = models.ForeignKey(Embargo)

    is_fork = models.BooleanField(default=False, db_index=True)
    forked_date = models.DateTimeField(db_index=True)

    title = models.CharField(validators=validate_title, max_length=200)
    description = models.TextField()
    # category = models.ForeignKey(Category, db_index=True)
    # node_license = models.ForeignKey(NodeLicenseRecord)

    public_comments = models.BooleanField(default=True)

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

    wiki_pages_current = DatetimeAwareJSONField()
    wiki_pages_versions = DatetimeAwareJSONField()
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = DatetimeAwareJSONField()
    file_guid_to_share_uuids = DatetimeAwareJSONField()

    # creator = models.ForeignKey(User, db_index=True)
    # contributors = models.ManyToManyField(User)
    # users_watching_node = models.ManyToManyField(User)

    # TODO: Logs should point to nodes
    # logs = models.
    # tags = models.ManyToManyField(Tag)

    # Tags for internal use
    # system_tags = models.ManyToManyField(Tag)

    nodes = models.ManyToManyField('self')
    forked_from = models.ForeignKey('self')
    registered_from = models.ForeignKey('self')
    root = models.ForeignKey('self')
    parent_node = models.ForeignKey('self')

    # The node (if any) used as a template for this node's creation
    template_node = models.ForeignKey('self')

    piwik_site_id = models.IntegerField()

    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    # TODO: Can this be a reference instead of data?
    child_node_subscriptions = DatetimeAwareJSONField()

    # alternative_citations = models.ManyToManyField(AlternativeCitation)

def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 200 characters.
    """
    if value is None or not value.strip():
        raise ValidationError('Title cannot be blank.')

    value = sanitize.strip_html(value)

    if value is None or not value.strip():
        raise ValidationError('Invalid title.')

    if len(value) > 200:
        raise ValidationError('Title cannot exceed 200 characters.')

    return True
