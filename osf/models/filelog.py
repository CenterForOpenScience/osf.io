from include import IncludeManager

from django.apps import apps
from django.db import models
from django.utils import timezone
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField


class FileLog(ObjectIDMixin, BaseModel):

    objects = IncludeManager()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    # Log action constants -- NOTE: templates stored in log_templates.mako
    CREATED_FROM = 'created_from'

    CHECKED_IN = 'checked_in'
    CHECKED_OUT = 'checked_out'

    FILE_TAG_ADDED = 'file_tag_added'
    FILE_TAG_REMOVED = 'file_tag_removed'

    FILE_MOVED = 'addon_file_moved'
    FILE_COPIED = 'addon_file_copied'
    FILE_RENAMED = 'addon_file_renamed'

    FOLDER_CREATED = 'folder_created'

    FILE_ADDED = 'file_added'
    FILE_UPDATED = 'file_updated'
    FILE_REMOVED = 'file_removed'
    FILE_RESTORED = 'file_restored'

    PREPRINT_FILE_UPDATED = 'preprint_file_updated'

    actions = ([CHECKED_IN, CHECKED_OUT, FILE_TAG_REMOVED, FILE_TAG_ADDED,
               FILE_MOVED, FILE_COPIED, FOLDER_CREATED, FILE_ADDED, FILE_UPDATED, FILE_REMOVED,
                FILE_RESTORED, PREPRINT_FILE_UPDATED, ] + list(sum([
                    config.actions for config in apps.get_app_configs() if config.name.startswith('addons.')
                ], tuple())))
    action_choices = [(action, action.upper()) for action in actions]
    project_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    date = NonNaiveDateTimeField(db_index=True, null=True, blank=True, default=timezone.now)
    # TODO build action choices on the fly with the addon stuff
    action = models.CharField(max_length=255, db_index=True)  # , choices=action_choices)
    user = models.ForeignKey('OSFUser', related_name='filelogs', db_index=True, null=True, blank=True)
    path = models.CharField(max_length=255, db_index=True, null=True)

    def __unicode__(self):
        return ('({self.action!r}, user={self.user!r},, file={self.file!r}, params={self.params!r}) '
                'with id {self.id!r}').format(self=self)

    class Meta:
        ordering = ['-date']
        get_latest_by = 'date'
