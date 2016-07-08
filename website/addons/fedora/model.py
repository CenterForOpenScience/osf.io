# -*- coding: utf-8 -*-
import os
import httplib as http
import logging

from flask import request
from modularodm import fields

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.sessions import session

from website.util import web_url_for
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, StorageAddonBase
from website.oauth.models import ExternalProvider

from website.addons.fedora import settings
from website.addons.fedora.serializer import FedoraSerializer

logger = logging.getLogger(__name__)

class FedoraUserSettings(AddonUserSettingsBase):

    @property
    def has_auth(self):
        return True


class FedoraNodeSettings(StorageAddonBase, AddonNodeSettingsBase):

    @property
    def complete(self):
        return True

    @property
    def has_auth(self):
        return True
