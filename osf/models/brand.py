from osf.models.base import BaseModel
from django.db import models

from website.util import api_v2_url


class Brand(BaseModel):
    """
    This model holds data custom styled assets for providers
    """

    name = models.CharField(max_length=30, blank=True, null=True)

    hero_logo_image = models.URLField()
    topnav_logo_image = models.URLField()
    hero_background_image = models.URLField()

    primary_color = models.CharField(max_length=7)
    secondary_color = models.CharField(max_length=7)

    def get_absolute_url(self):
        return api_v2_url('brands/{}/'.format(self.id))
