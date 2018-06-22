from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save

from addons.osfstorage.models import OsfStorageFolder


class UploadMixin(models.Model):
    root_folder = models.ForeignKey(OsfStorageFolder, null=True, blank=True, related_name='%(class)s_object')

    class Meta:
        abstract = True


@receiver(post_save, sender='osf.Preprint')
def create_file_node(sender, instance, **kwargs):
    if instance.root_folder_id:
        return

    # Note: The "root" node will always be "named" empty string
    root_folder = OsfStorageFolder(name='', target=instance, is_root=True)
    root_folder.save()

    instance.__class__.objects.filter(id=instance.id).update(root_folder=root_folder)
    instance.refresh_from_db()
