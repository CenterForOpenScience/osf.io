from django.db import models
from framework.mongo import ObjectId
from osf_models.models.base import BaseModel
from osf_models.utils.datetime_aware_jsonfield import DatetimeAwareJSONField


def get_object_id():
    return str(ObjectId())


class NodeLog(BaseModel):
    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'
    ACTIONS = (('created_from', 'CREATED_FROM'),
               ('project_created', 'PROJECT_CREATED'),
               ('project_registered', 'PROJECT_REGISTERED'),
               ('project_deleted', 'PROJECT_DELETED'),
               ('node_created', 'NODE_CREATED'),
               ('node_forked', 'NODE_FORKED'),
               ('node_removed', 'NODE_REMOVED'),
               ('pointer_created', 'POINTER_CREATED'),
               ('pointer_forked', 'POINTER_FORKED'),
               ('pointer_removed', 'POINTER_REMOVED'),
               ('wiki_updated', 'WIKI_UPDATED'),
               ('wiki_deleted', 'WIKI_DELETED'),
               ('wiki_renamed', 'WIKI_RENAMED'),
               ('made_wiki_public', 'MADE_WIKI_PUBLIC'),
               ('made_wiki_private', 'MADE_WIKI_PRIVATE'),
               ('contributor_added', 'CONTRIB_ADDED'),
               ('contributor_removed', 'CONTRIB_REMOVED'),
               ('contributors_reordered', 'CONTRIB_REORDERED'),
               ('permissions_updated', 'PERMISSIONS_UPDATED'),
               ('made_private', 'MADE_PRIVATE'),
               ('made_public', 'MADE_PUBLIC'),
               ('tag_added', 'TAG_ADDED'),
               ('tag_removed', 'TAG_REMOVED'),
               ('edit_title', 'EDITED_TITLE'),
               ('edit_description', 'EDITED_DESCRIPTION'),
               ('license_changed', 'CHANGED_LICENSE'),
               ('updated_fields', 'UPDATED_FIELDS'),
               ('addon_file_moved', 'FILE_MOVED'),
               ('addon_file_copied', 'FILE_COPIED'),
               ('addon_file_renamed', 'FILE_RENAMED'),
               ('folder_created', 'FOLDER_CREATED'),
               ('file_added', 'FILE_ADDED'),
               ('file_updated', 'FILE_UPDATED'),
               ('file_removed', 'FILE_REMOVED'),
               ('file_restored', 'FILE_RESTORED'),
               ('addon_added', 'ADDON_ADDED'),
               ('addon_removed', 'ADDON_REMOVED'),
               ('comment_added', 'COMMENT_ADDED'),
               ('comment_removed', 'COMMENT_REMOVED'),
               ('comment_updated', 'COMMENT_UPDATED'),
               ('comment_restored', 'COMMENT_RESTORED'),
               ('citation_added', 'CITATION_ADDED'),
               ('citation_edited', 'CITATION_EDITED'),
               ('citation_removed', 'CITATION_REMOVED'),
               ('made_contributor_visible', 'MADE_CONTRIBUTOR_VISIBLE'),
               ('made_contributor_invisible', 'MADE_CONTRIBUTOR_INVISIBLE'),
               ('external_ids_added', 'EXTERNAL_IDS_ADDED'),
               ('embargo_approved', 'EMBARGO_APPROVED'),
               ('embargo_cancelled', 'EMBARGO_CANCELLED'),
               ('embargo_completed', 'EMBARGO_COMPLETED'),
               ('embargo_initiated', 'EMBARGO_INITIATED'),
               ('retraction_approved', 'RETRACTION_APPROVED'),
               ('retraction_cancelled', 'RETRACTION_CANCELLED'),
               ('retraction_initiated', 'RETRACTION_INITIATED'),
               ('registration_cancelled', 'REGISTRATION_APPROVAL_CANCELLED'),
               ('registration_initiated', 'REGISTRATION_APPROVAL_INITIATED'),
               ('registration_approved', 'REGISTRATION_APPROVAL_APPROVED'),
               ('primary_institution_changed', 'PRIMARY_INSTITUTION_CHANGED'),
               ('primary_institution_removed',
                'PRIMARY_INSTITUTION_REMOVED'), )

    guid = models.CharField(max_length=255,
                            unique=True,
                            db_index=True,
                            default=get_object_id)

    date = models.DateTimeField(db_index=True, null=True)#, auto_now_add=True)
    action = models.CharField(max_length=255, db_index=True, choices=ACTIONS)
    params = DatetimeAwareJSONField(default={})
    should_hide = models.BooleanField(default=False)

    # was_connected_to = models.ManyToManyField('Node')

    user = models.ForeignKey('User', related_name='logs', db_index=True, null=True)
    foreign_user = models.CharField(max_length=255, blank=True)
    node = models.ForeignKey('Node', related_name='logs', db_index=True, null=True)

    @property
    def _id(self):
        return self.guid
