from django.db import models

from addons.osfstorage.models import OsfStorageFolder


class UploadMixin(models.Model):
    root_folder = models.ForeignKey(OsfStorageFolder, null=True, blank=True, related_name='%(class)s_object')

    class Meta:
        abstract = True
