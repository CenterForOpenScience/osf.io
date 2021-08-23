from include import IncludeManager

from django.apps import apps
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from website.util import api_v2_url


class PreprintLog(ObjectIDMixin, BaseModel):
    FIELD_ALIASES = {
        # TODO: Find a better way
        'preprint': 'preprint__guids___id',
        'user': 'user__guids___id',
    }

    objects = IncludeManager()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    DELETED = 'deleted'

    CONTRIB_ADDED = 'contributor_added'
    CONTRIB_REMOVED = 'contributor_removed'
    CONTRIB_REORDERED = 'contributors_reordered'
    PERMISSIONS_UPDATED = 'permissions_updated'
    MADE_CONTRIBUTOR_VISIBLE = 'made_contributor_visible'
    MADE_CONTRIBUTOR_INVISIBLE = 'made_contributor_invisible'

    MADE_PRIVATE = 'made_private'
    MADE_PUBLIC = 'made_public'

    TAG_ADDED = 'tag_added'
    TAG_REMOVED = 'tag_removed'

    EDITED_TITLE = 'edit_title'
    EDITED_DESCRIPTION = 'edit_description'
    CHANGED_LICENSE = 'license_changed'

    FILE_UPDATED = 'file_updated'
    FILE_METADATA_UPDATED = 'file_metadata_updated'

    SUBJECTS_UPDATED = 'subjects_updated'

    SUPPLEMENTAL_NODE_ADDED = 'supplement_node_added'
    SUPPLEMENTAL_NODE_REMOVED = 'supplement_node_removed'

    PUBLISHED = 'published'

    UPDATE_HAS_COI = 'has_coi_updated'
    UPDATE_COI_STATEMENT = 'coi_statement_updated'
    UPDATE_HAS_DATA_LINKS = 'has_data_links_updated'
    UPDATE_WHY_NO_DATA = 'why_no_data_updated'
    UPDATE_DATA_LINKS = 'data_links_updated'
    UPDATE_HAS_PREREG_LINKS = 'has_prereg_links_updated'
    UPDATE_WHY_NO_PREREG = 'why_no_prereg_updated'
    UPDATE_PREREG_LINKS = 'prereg_links_updated'
    UPDATE_PREREG_LINKS_INFO = 'prereg_links_info_updated'

    CONFIRM_HAM = 'confirm_ham'
    FLAG_SPAM = 'flag_spam'
    CONFIRM_SPAM = 'confirm_spam'

    actions = ([
        DELETED,
        CONTRIB_ADDED,
        CONTRIB_REMOVED,
        CONTRIB_REORDERED,
        PERMISSIONS_UPDATED,
        TAG_ADDED,
        TAG_REMOVED,
        EDITED_TITLE,
        CHANGED_LICENSE,
        EDITED_DESCRIPTION,
        FILE_UPDATED,
        FILE_METADATA_UPDATED,
        MADE_CONTRIBUTOR_VISIBLE,
        SUPPLEMENTAL_NODE_ADDED,
        MADE_CONTRIBUTOR_INVISIBLE,
        SUBJECTS_UPDATED,
        MADE_PRIVATE,
        MADE_PUBLIC,
        PUBLISHED,
        UPDATE_HAS_COI,
        UPDATE_COI_STATEMENT,
        UPDATE_HAS_DATA_LINKS,
        UPDATE_WHY_NO_DATA,
        UPDATE_DATA_LINKS,
        UPDATE_HAS_PREREG_LINKS,
        UPDATE_WHY_NO_PREREG,
        UPDATE_PREREG_LINKS,
        UPDATE_PREREG_LINKS_INFO,
        CONFIRM_HAM,
        FLAG_SPAM,
        CONFIRM_SPAM,
    ] + list(sum([config.actions for config in apps.get_app_configs() if config.name.startswith('addons.')], tuple())))

    action_choices = [(action, action.upper()) for action in actions]
    # TODO build action choices on the fly with the addon stuff
    action = models.CharField(max_length=255, db_index=True)  # , choices=action_choices)
    params = DateTimeAwareJSONField(default=dict)
    should_hide = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', related_name='preprint_logs', db_index=True,
                             null=True, blank=True, on_delete=models.CASCADE)
    foreign_user = models.CharField(max_length=255, null=True, blank=True)
    preprint = models.ForeignKey('Preprint', related_name='logs',
                             db_index=True, null=True, blank=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return ('({self.action!r}, user={self.user!r}, preprint={self.preprint!r}, params={self.params!r}) '
                'with id {self.id!r}').format(self=self)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

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
