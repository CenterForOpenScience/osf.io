from include import IncludeManager

from django.apps import apps
from django.db import models
from django.utils import timezone
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from website.util import api_v2_url


class NodeLog(ObjectIDMixin, BaseModel):
    FIELD_ALIASES = {
        # TODO: Find a better way
        'node': 'node__guids___id',
        'user': 'user__guids___id',
        'original_node': 'original_node__guids___id'
    }

    objects = IncludeManager()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    # Log action constants -- NOTE: templates stored in log_templates.mako
    CREATED_FROM = 'created_from'

    PROJECT_CREATED = 'project_created'
    PROJECT_REGISTERED = 'project_registered'
    PROJECT_DELETED = 'project_deleted'

    NODE_CREATED = 'node_created'
    NODE_FORKED = 'node_forked'
    NODE_REMOVED = 'node_removed'

    POINTER_CREATED = NODE_LINK_CREATED = 'pointer_created'
    POINTER_FORKED = NODE_LINK_FORKED = 'pointer_forked'
    POINTER_REMOVED = NODE_LINK_REMOVED = 'pointer_removed'

    WIKI_UPDATED = 'wiki_updated'
    WIKI_DELETED = 'wiki_deleted'
    WIKI_RENAMED = 'wiki_renamed'

    MADE_WIKI_PUBLIC = 'made_wiki_public'
    MADE_WIKI_PRIVATE = 'made_wiki_private'

    CONTRIB_ADDED = 'contributor_added'
    CONTRIB_REMOVED = 'contributor_removed'
    CONTRIB_REORDERED = 'contributors_reordered'

    CHECKED_IN = 'checked_in'
    CHECKED_OUT = 'checked_out'

    PERMISSIONS_UPDATED = 'permissions_updated'

    MADE_PRIVATE = 'made_private'
    MADE_PUBLIC = 'made_public'

    TAG_ADDED = 'tag_added'
    TAG_REMOVED = 'tag_removed'

    FILE_TAG_ADDED = 'file_tag_added'
    FILE_TAG_REMOVED = 'file_tag_removed'

    EDITED_TITLE = 'edit_title'
    EDITED_DESCRIPTION = 'edit_description'
    CHANGED_LICENSE = 'license_changed'

    UPDATED_FIELDS = 'updated_fields'

    FILE_MOVED = 'addon_file_moved'
    FILE_COPIED = 'addon_file_copied'
    FILE_RENAMED = 'addon_file_renamed'

    FOLDER_CREATED = 'folder_created'

    FILE_ADDED = 'file_added'
    FILE_UPDATED = 'file_updated'
    FILE_REMOVED = 'file_removed'
    FILE_RESTORED = 'file_restored'

    ADDON_ADDED = 'addon_added'
    ADDON_REMOVED = 'addon_removed'
    COMMENT_ADDED = 'comment_added'
    COMMENT_REMOVED = 'comment_removed'
    COMMENT_UPDATED = 'comment_updated'
    COMMENT_RESTORED = 'comment_restored'

    CITATION_ADDED = 'citation_added'
    CITATION_EDITED = 'citation_edited'
    CITATION_REMOVED = 'citation_removed'

    MADE_CONTRIBUTOR_VISIBLE = 'made_contributor_visible'
    MADE_CONTRIBUTOR_INVISIBLE = 'made_contributor_invisible'

    EXTERNAL_IDS_ADDED = 'external_ids_added'

    EMBARGO_APPROVED = 'embargo_approved'
    EMBARGO_CANCELLED = 'embargo_cancelled'
    EMBARGO_COMPLETED = 'embargo_completed'
    EMBARGO_INITIATED = 'embargo_initiated'
    EMBARGO_TERMINATED = 'embargo_terminated'

    RETRACTION_APPROVED = 'retraction_approved'
    RETRACTION_CANCELLED = 'retraction_cancelled'
    RETRACTION_INITIATED = 'retraction_initiated'

    REGISTRATION_APPROVAL_CANCELLED = 'registration_cancelled'
    REGISTRATION_APPROVAL_INITIATED = 'registration_initiated'
    REGISTRATION_APPROVAL_APPROVED = 'registration_approved'
    PREREG_REGISTRATION_INITIATED = 'prereg_registration_initiated'

    AFFILIATED_INSTITUTION_ADDED = 'affiliated_institution_added'
    AFFILIATED_INSTITUTION_REMOVED = 'affiliated_institution_removed'

    PREPRINT_INITIATED = 'preprint_initiated'
    PREPRINT_FILE_UPDATED = 'preprint_file_updated'
    PREPRINT_LICENSE_UPDATED = 'preprint_license_updated'

    SUBJECTS_UPDATED = 'subjects_updated'

    VIEW_ONLY_LINK_ADDED = 'view_only_link_added'
    VIEW_ONLY_LINK_REMOVED = 'view_only_link_removed'

    actions = ([CHECKED_IN, CHECKED_OUT, FILE_TAG_REMOVED, FILE_TAG_ADDED, CREATED_FROM, PROJECT_CREATED,
                PROJECT_REGISTERED, PROJECT_DELETED, NODE_CREATED, NODE_FORKED, NODE_REMOVED,
                NODE_LINK_CREATED, NODE_LINK_FORKED, NODE_LINK_REMOVED, WIKI_UPDATED,
                WIKI_DELETED, WIKI_RENAMED, MADE_WIKI_PUBLIC,
                MADE_WIKI_PRIVATE, CONTRIB_ADDED, CONTRIB_REMOVED, CONTRIB_REORDERED,
                PERMISSIONS_UPDATED, MADE_PRIVATE, MADE_PUBLIC, TAG_ADDED, TAG_REMOVED, EDITED_TITLE,
                EDITED_DESCRIPTION, UPDATED_FIELDS, FILE_MOVED, FILE_COPIED,
                FOLDER_CREATED, FILE_ADDED, FILE_UPDATED, FILE_REMOVED, FILE_RESTORED, ADDON_ADDED,
                ADDON_REMOVED, COMMENT_ADDED, COMMENT_REMOVED, COMMENT_UPDATED, COMMENT_RESTORED,
                MADE_CONTRIBUTOR_VISIBLE,
                MADE_CONTRIBUTOR_INVISIBLE, EXTERNAL_IDS_ADDED, EMBARGO_APPROVED, EMBARGO_TERMINATED,
                EMBARGO_CANCELLED, EMBARGO_COMPLETED, EMBARGO_INITIATED, RETRACTION_APPROVED,
                RETRACTION_CANCELLED, RETRACTION_INITIATED, REGISTRATION_APPROVAL_CANCELLED,
                REGISTRATION_APPROVAL_INITIATED, REGISTRATION_APPROVAL_APPROVED,
                PREREG_REGISTRATION_INITIATED,
                CITATION_ADDED, CITATION_EDITED, CITATION_REMOVED,
                AFFILIATED_INSTITUTION_ADDED, AFFILIATED_INSTITUTION_REMOVED, PREPRINT_INITIATED,
                PREPRINT_FILE_UPDATED, PREPRINT_LICENSE_UPDATED, VIEW_ONLY_LINK_ADDED, VIEW_ONLY_LINK_REMOVED] + list(sum([
                    config.actions for config in apps.get_app_configs() if config.name.startswith('addons.')
                ], tuple())))
    action_choices = [(action, action.upper()) for action in actions]
    date = NonNaiveDateTimeField(db_index=True, null=True, blank=True, default=timezone.now)
    # TODO build action choices on the fly with the addon stuff
    action = models.CharField(max_length=255, db_index=True)  # , choices=action_choices)
    params = DateTimeAwareJSONField(default=dict)
    should_hide = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', related_name='logs', db_index=True,
                             null=True, blank=True, on_delete=models.CASCADE)
    foreign_user = models.CharField(max_length=255, null=True, blank=True)
    node = models.ForeignKey('AbstractNode', related_name='logs',
                             db_index=True, null=True, blank=True, on_delete=models.CASCADE)
    original_node = models.ForeignKey('AbstractNode', db_index=True,
                                      null=True, blank=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return ('({self.action!r}, user={self.user!r},, node={self.node!r}, params={self.params!r}) '
                'with id {self.id!r}').format(self=self)

    class Meta:
        ordering = ['-date']
        get_latest_by = 'date'

    @property
    def absolute_api_v2_url(self):
        path = '/logs/{}/'.format(self._id)
        return api_v2_url(path)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_url(self):
        return self.absolute_api_v2_url

    def _natural_key(self):
        return self._id
