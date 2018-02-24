# -*- coding: utf-8 -*-
import logging
import json

from addons.base.models import BaseNodeSettings
from django.db import models

logger = logging.getLogger(__name__)


class NodeSettings(BaseNodeSettings):
    service_list = models.TextField(blank=True, null=True)

    def get_services(self):
        if self.service_list is None or self.service_list == '':
            return []
        r = json.loads(self.service_list)
        return [(e['name'], e['base_url']) for e in r]

    def set_services(self, services):
        data = [{'name': name,
                 'base_url': base_url} for name, base_url in services]
        self.service_list = json.dumps(data)
        self.save()
