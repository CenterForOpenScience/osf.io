# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from .. import SHORT_NAME


def remove_fields(json_entities, fields=None):
    if fields is None:
        return json_entities
    return dict([(k, v) for k, v in json_entities.items() if k not in fields])


class BaseAddonTestCase(AddonTestCase):
    ADDON_SHORT_NAME = SHORT_NAME
    OWNERS = ['node']
    NODE_USER_FIELD = None
    ExternalAccountFactory = None
    Provider = None
    Serializer = None
    client = None

    def set_node_settings(self, settings):
        return
