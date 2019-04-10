from osf.models import OSFUser
from osf.quickfiles.legacy_quickfiles import QuickFilesNode
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.contrib.contenttypes.models import ContentType


def _create_quickfiles(instance):
    QuickFolder = apps.get_model('osf', 'QuickFolder')
    content_type_id = ContentType.objects.get_for_model(OSFUser).id
    quickfiles = QuickFolder(target_object_id=instance.id,
                             target_content_type_id=content_type_id,
                             provider=QuickFolder._provider,
                             path='/')
    quickfiles.save()


@receiver(post_save, sender=OSFUser)
def create_quickfiles(sender, instance, created, **kwargs):
    if created:
        _create_quickfiles(instance)


def _create_quickfiles_project(instance):
    QuickFilesNode.objects.create_for_user(instance)


def create_quickfiles_project(sender, instance, created, **kwargs):
    if created:
        _create_quickfiles_project(instance)
