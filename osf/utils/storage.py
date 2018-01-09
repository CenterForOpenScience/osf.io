from __future__ import absolute_import

import urlparse
from django.db import models
from website import settings as osf_settings
from api.base import settings as api_settings

from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible


class BannerImage(models.Model):
    filename = models.TextField(unique=True)
    image = models.BinaryField()

@deconstructible
class BannerImageStorage(Storage):
    media_url = urlparse.urljoin(osf_settings.API_DOMAIN, '_{}'.format(api_settings.MEDIA_URL))
    def _open(self, name, mode='rb'):
        assert mode == 'rb'
        icon = BannerImage.objects.get(filename=name)
        return ContentFile(icon.image)

    def _save(self, name, content):
        BannerImage.objects.update_or_create(filename=name, defaults={'image': content.read()})
        return name

    def delete(self, name):
        BannerImage.objects.get(filename=name).delete()

    def get_available_name(self, name, max_length=None):
        return name

    def url(self, name):
        return urlparse.urljoin(self.media_url, name)
