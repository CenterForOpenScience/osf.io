

from django.db import models
from website.util import api_v2_url

from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible

# Could easily be genericized - would just need a generic url to serve images
class BannerImage(models.Model):
    filename = models.CharField(unique=True, max_length=256)
    image = models.BinaryField()

@deconstructible
class BannerImageStorage(Storage):
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        icon = BannerImage.objects.get(filename=name)
        return ContentFile(icon.image)

    def _save(self, name, content):
        BannerImage.objects.update_or_create(filename=name, defaults={'image': content.read()})
        return name

    def delete(self, name):
        BannerImage.objects.get(filename=name).delete()

    # Note: Banner image names must be unique
    def get_available_name(self, name, max_length=None):
        return name

    def url(self, name):
        return api_v2_url('/banners/{}/'.format(name), base_prefix='_/')
