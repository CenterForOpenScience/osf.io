from osf.models.base import BaseModel
from django.db import models
from colorfield.fields import ColorField


class BrandAssets(BaseModel):
    """
    This model holds data custom styled assets for providers
    """

    hero_logo = models.URLField()
    topnav_logo = models.URLField()
    hero_background = ColorField()
