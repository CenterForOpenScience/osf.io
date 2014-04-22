# -*- coding: utf-8 -*-
import logging

from modularodm.validators import (
    URLValidator, MinValueValidator, MaxValueValidator
)

from framework import fields
from website.addons.base import AddonNodeSettingsBase


logger = logging.getLogger(__name__)
debug = logger.debug


class ForwardNodeSettings(AddonNodeSettingsBase):

    url = fields.StringField(validate=URLValidator())
    redirect_bool = fields.BooleanField(default=True, validate=True)
    redirect_secs = fields.IntegerField(
        default=15,
        validate=[MinValueValidator(15), MaxValueValidator(60)]
    )
