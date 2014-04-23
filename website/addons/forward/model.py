# -*- coding: utf-8 -*-
from modularodm.validators import (
    URLValidator, MinValueValidator, MaxValueValidator
)

from framework import fields

from website.addons.base import AddonNodeSettingsBase


class ForwardNodeSettings(AddonNodeSettingsBase):

    url = fields.StringField(validate=URLValidator())
    redirect_bool = fields.BooleanField(default=True, validate=True)
    redirect_secs = fields.IntegerField(
        default=15,
        validate=[MinValueValidator(5), MaxValueValidator(60)]
    )
