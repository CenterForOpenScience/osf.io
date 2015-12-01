# -*- coding: utf-8 -*-

import os
import urlparse
import itertools
import httplib as http

import pymongo
from modularodm import fields

from framework.auth import Auth
from framework.mongo import StoredObject

from website import settings
from website.util import web_url_for
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.dryad import utils
from website.addons.dryad import settings as dryad_settings


class AddonDryadUserSettings(AddonUserSettingsBase):
	#TODO: Put in the user settings here:
    def delete(self, save=False):
        super(AddonDryadUserSettings, self).delete(save=save)


class AddonDryadNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
	dryad_title = fields.StringField()
	dryad_doi = fields.StringField()

	def delete(self):
		self.deauthorize(Auth(self.user_settings.owner), add_log=False)
		super(AddonDataverseNodeSettings, self).delete()


	def serialize_waterbutler_credentials(self):
		return {'token': ''}
	def serialize_waterbutler_settings(self):
		return {
			'title': self.dryad_title,
			'doi': self.dryad_doi,
		}
	def create_waterbutler_log(self, auth, action, metadata):
		self.owner.add_log(
				'dryad_{0}'.format(action),
				auth=auth,
				params={},
	    	)