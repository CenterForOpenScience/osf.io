from django.db import models

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import EncryptedJSONField
from website import settings as website_settings
from website.util import api_v2_url


class Region(models.Model):
    _id = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=200)
    waterbutler_credentials = EncryptedJSONField(default=dict)
    waterbutler_url = models.URLField(default=website_settings.WATERBUTLER_URL)
    mfr_url = models.URLField(default=website_settings.MFR_SERVER_URL)
    waterbutler_settings = DateTimeAwareJSONField(default=dict)

    def __unicode__(self):
        return '{}'.format(self.name)

    def get_absolute_url(self):
        return '{}regions/{}'.format(self.absolute_api_v2_url, self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/regions/{}/'.format(self._id)
        return api_v2_url(path)

    class Meta:
        unique_together = ('_id', 'name')
