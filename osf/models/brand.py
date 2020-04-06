from osf.models.base import BaseModel
from django.db import models


class Brand(BaseModel):
    """
    This model holds data custom styled assets for providers
    """

    class Meta:
        # Custom permissions for use in the OSF Admin App
        permissions = (
            ('view_brand', 'Can view brand details'),
            ('modify_brand', 'Can modify brands')
        )

    name = models.CharField(max_length=30, blank=True, null=True)

    hero_logo_image = models.URLField()
    topnav_logo_image = models.URLField()
    hero_background_image = models.URLField()

    primary_color = models.CharField(max_length=7)
    secondary_color = models.CharField(max_length=7)
