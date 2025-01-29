# -*- coding: utf-8 -*-
import logging

from addons.base.models import BaseNodeSettings
from django.db import models
from . import settings

logger = logging.getLogger(__name__)

class NodeSettings(BaseNodeSettings):

    office_server = models.TextField(blank=True, null=True)

    def get_office_server(self):
        if self.office_server is None or self.office_server == '':
            return settings.WOPI_CLIENT_ONLYOFFICE
        return self.office_server

    def set_office_server(self, office_server):
        self.office_server = office_server
        self.save()
