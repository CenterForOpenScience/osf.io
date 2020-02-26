# -*- coding: utf-8 -*-
from osf.utils.requests import get_request_and_user_id, get_headers_from_request

from addons.base.models import BaseNodeSettings
from dirtyfields import DirtyFieldsMixin
from django.db import models
from osf.exceptions import ValidationValueError
from osf.models.validators import validate_no_html
from osf.models import OSFUser


class NodeSettings(DirtyFieldsMixin, BaseNodeSettings):
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

    def save(self, request=None, *args, **kwargs):
        super(NodeSettings, self).save(*args, **kwargs)
        if request:
            if not hasattr(request, 'user'):  # TODO: remove when Flask is removed
                _, user_id = get_request_and_user_id()
                user = OSFUser.load(user_id)
            else:
                user = request.user

            self.owner.check_spam(user, {'addons_forward_node_settings__url'}, get_headers_from_request(request))

    def clean(self):
        if self.url and self.owner._id in self.url:
            raise ValidationValueError('Circular URL')
