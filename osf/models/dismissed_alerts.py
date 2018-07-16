from django.db import models
from website.util import api_v2_url

from .base import BaseModel


class DismissedAlert(BaseModel):
    """User dismissed alerts
    """
    primary_identifier_name = '_id'

    _id = models.CharField(max_length=255, db_index=True)
    # User who dismissed this alert
    user = models.ForeignKey('OSFUser', related_name='alerts', on_delete=models.CASCADE)
    # Path of the page where this alert is displayed e.g: /ezcuj/settings
    location = models.CharField(max_length=255)

    def __unicode__(self):
        return '{}'.format(self._id)

    # Properties used by Django and DRF "Links: self" field
    @property
    def absolute_api_v2_url(self):
        path = '/alerts/{}/'.format(self._id)
        return api_v2_url(path)

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    class Meta:
        unique_together = ('_id', 'location')
        ordering = ['-created']
        get_latest_by = 'created'
