from osf.models.base import BaseModel
from django.db import models
<<<<<<< HEAD
=======
from colorfield.fields import ColorField
>>>>>>> add Brand model with migration


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
