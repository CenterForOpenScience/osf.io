from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save

from addons.osfstorage.models import OsfStorageFolder


class UploadMixin(models.Model):
    root_folder = models.ForeignKey(OsfStorageFolder, null=True, blank=True)

    class Meta:
        abstract = True


# hopefully this works; if not, then overrdie save in UploadMixin
@receiver(post_save, sender='osf.PreprintService')
def create_file_node(sender, instance, **kwargs):
    if instance.root_folder:
        return

    # Note: The "root" node will always be "named" empty string
    root_folder = OsfStorageFolder(name='', target=instance)
    root_folder.save()

    instance.__class__.objects.filter(id=instance.id).update(root_folder=root_folder)
    instance.refresh_from_db()
