from django.db import models
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.models.baselog import BaseLog


class UserLog(BaseLog):
    FIELD_ALIASES = {
        # TODO: Find a better way
        'user': 'user__guids___id',
    }

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    # Log action constants -- NOTE: templates stored in log_templates.mako
    FILE_TAG_ADDED = 'file_tag_added'
    FILE_TAG_REMOVED = 'file_tag_removed'

    FILE_METADATA_UPDATED = 'file_metadata_updated'

    FILE_MOVED = 'addon_file_moved'
    FILE_COPIED = 'addon_file_copied'
    FILE_RENAMED = 'addon_file_renamed'

    FOLDER_CREATED = 'folder_created'

    FILE_ADDED = 'file_added'
    FILE_UPDATED = 'file_updated'
    FILE_REMOVED = 'file_removed'
    FILE_RESTORED = 'file_restored'

    actions = (FILE_TAG_REMOVED, FILE_TAG_ADDED, FILE_MOVED, FILE_COPIED, FILE_METADATA_UPDATED,
               FOLDER_CREATED, FILE_ADDED, FILE_UPDATED, FILE_REMOVED, FILE_RESTORED)

    action_choices = [(action, action.upper()) for action in actions]
    action = models.CharField(max_length=255, db_index=True, choices=action_choices)
    params = DateTimeAwareJSONField(default=dict)
    user = models.ForeignKey('OSFUser', related_name='user_logs', db_index=True,
                             null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
