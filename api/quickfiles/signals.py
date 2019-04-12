from osf.models import OSFUser
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.contrib.contenttypes.models import ContentType


def _create_quickfiles(instance):
    """
    This underscored function is just here to make `create_quickfiles` easier to mock for test speed ups.
    :param instance:
    :return:
    """
    QuickFolder = apps.get_model('osf', 'QuickFolder')
    content_type_id = ContentType.objects.get_for_model(OSFUser).id
    quickfiles = QuickFolder(
        target_object_id=instance.id,
        target_content_type_id=content_type_id,
        provider=QuickFolder._provider,
        path='/',
    )
    quickfiles.save()


@receiver(post_save, sender=OSFUser)
def create_quickfiles(sender, instance, created, **kwargs):
    if created:
        _create_quickfiles(instance)
