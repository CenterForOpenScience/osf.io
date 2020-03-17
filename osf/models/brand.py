from osf.models.base import BaseModel
from django.db import models
from colorfield.fields import ColorField


class Brand(BaseModel):
    """
    This model holds data custom styled assets for providers
    """

    hero_logo_image = models.URLField()
    topnav_logo_image = models.URLField()
    hero_background_image = models.URLField()

    primary_color = ColorField()
    secondary_color = ColorField()
