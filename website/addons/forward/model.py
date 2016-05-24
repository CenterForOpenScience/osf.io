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

    @property
    def link_text(self):
        return self.label if self.label else self.url

    def on_delete(self):
        self.reset()

    def reset(self):
        self.url = None
        self.label = None


@ForwardNodeSettings.subscribe('before_save')
def validate_circular_reference(schema, instance):
    """Prevent node from forwarding to itself."""
    if instance.url and instance.owner._id in instance.url:
        raise ValidationValueError('Circular URL')
