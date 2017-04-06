# -*- coding: utf-8 -*-

from addons.base.models import BaseNodeSettings
from dirtyfields import DirtyFieldsMixin
from django.db import models
from osf.exceptions import ValidationValueError
from osf.models.validators import validate_no_html


class NodeSettings(DirtyFieldsMixin, BaseNodeSettings):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.addons.forward.model.ForwardNodeSettings'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    complete = True
    has_auth = True

    url = models.URLField(blank=True, null=True, max_length=255)  # 242 on prod
    label = models.TextField(blank=True, null=True, validators=[validate_no_html])

    @property
    def link_text(self):
        return self.label if self.label else self.url

    def on_delete(self):
        self.reset()

    def reset(self):
        self.url = None
        self.label = None

    def after_register(self, node, registration, user, save=True):
        clone = self.clone()
        clone.owner = registration
        clone.on_add()
        clone.save()

        return clone, None

    def clean(self):
        if self.url and self.owner._id in self.url:
            raise ValidationValueError('Circular URL')
