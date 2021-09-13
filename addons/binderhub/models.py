import logging

from osf.models.base import BaseModel
from osf.models.user import OSFUser
from osf.models.node import AbstractNode
from addons.base.models import BaseNodeSettings
from django.db import models
from . import settings

logger = logging.getLogger(__name__)


class BinderHubToken(BaseModel):
    user = models.ForeignKey(OSFUser, related_name='binderhub_token', db_index=True,
                             null=True, blank=True, on_delete=models.CASCADE)

    node = models.ForeignKey(AbstractNode, related_name='binderhub_token',
                             db_index=True, null=True, blank=True, on_delete=models.CASCADE)

    binderhub_token = models.TextField(blank=True, null=True)

    jupyterhub_url = models.TextField(blank=True, null=True)

    jupyterhub_token = models.TextField(blank=True, null=True)


class NodeSettings(BaseNodeSettings):
    binder_url = models.TextField(blank=True, null=True)

    def get_binder_url(self):
        if self.binder_url is None or self.binder_url == '':
            return settings.DEFAULT_BINDER_URL
        return self.binder_url

    def set_binder_url(self, binder_url):
        self.binder_url = binder_url
        self.save()

    @property
    def complete(self):
        return True
