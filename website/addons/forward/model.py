# -*- coding: utf-8 -*-

from modularodm import fields
from modularodm.validators import (
    URLValidator, MinValueValidator, MaxValueValidator
)
from modularodm.exceptions import ValidationValueError

from framework.mongo.utils import sanitized

from website.addons.base import AddonNodeSettingsBase


class ForwardNodeSettings(AddonNodeSettingsBase):

    complete = True

    url = fields.StringField(validate=URLValidator())
    label = fields.StringField(validate=sanitized)
    redirect_bool = fields.BooleanField(default=True, validate=True)
    redirect_secs = fields.IntegerField(
        default=15,
        validate=[MinValueValidator(5), MaxValueValidator(60)]
    )

    @property
    def link_text(self):
        return self.label if self.label else self.url

    def on_delete(self):
        self.reset()

    def reset(self):
        self.url = None
        self.label = None
        self.redirect_bool = True
        self.redirect_secs = 15


@ForwardNodeSettings.subscribe('before_save')
def validate_circular_reference(schema, instance):
    """Prevent node from forwarding to itself."""
    if instance.url and instance.owner._id in instance.url:
        raise ValidationValueError('Circular URL')
