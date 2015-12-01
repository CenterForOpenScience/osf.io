# -*- coding: utf-8 -*-

import os
import urlparse
import itertools
import httplib as http

import pymongo
from modularodm import fields

from framework.auth import Auth
from framework.mongo import StoredObject
from website.oauth.models import ExternalProvider

from website import settings
from website.util import web_url_for
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.dryad import utils
from website.addons.dryad import settings as dryad_settings
from website.addons.dryad import serializer as serializer
from website.addons.dryad.utils import DryadNodeLogger



class AddonDryadUserSettings(AddonUserSettingsBase):
	serializer = serializer.DryadSerializer
	#TODO: Put in the user settings here:
	def delete(self, **kwargs):
		super(AddonDryadUserSettings, self).delete()
	@property
	def has_auth(self):
	    return True


class AddonDryadNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
	"""
	A Dryad node is a collection of packages. Each package is specified by a DOI, and the title is saved automatically
	"""
	#packages = fields.ForeignField('AddonDryadPackage', list=True)
	serializer = serializer.DryadSerializer
	dryad_metadata = fields.StringField(list=True)
	dryad_title = fields.StringField()
	dryad_doi = fields.StringField()
	dryad_doi_list = fields.StringField(list=True)
	complete = True
	has_auth = True
	provider_name = 'dryad'

	user_settings = fields.ForeignField(
	    'addondryadusersettings', backref='authorized'
	)

	def delete(self, **kwargs):
		dryad_doi_list = None
		super(AddonDryadNodeSettings, self).delete()

	@property
	def folder_name(self):

		return ""

	def serialize_waterbutler_credentials(self):
		return {'storage':{}}
	def serialize_waterbutler_settings(self):
		settings=dryad_settings.WATERBUTLER_SETTINGS
		#modify the settings here.
		settings['doi_list'] = self.dryad_doi_list
		return settings


	def create_waterbutler_log(self, auth, action, metadata):
		path = metadata['path']
		print path

		url = self.owner.web_url_for('addon_view_or_download_file', path=path, provider='dryad')
		if not metadata.get('extra'):
		    sha = None
		    urls = {}
		else:
		    sha = metadata['extra']['commit']['sha']
		    urls = {
		        'view': '{0}?ref={1}'.format(url, sha),
		        'download': '{0}?action=download&ref={1}'.format(url, sha)
		    }

		self.owner.add_log(
		    'dryad_{0}'.format(action),
		    auth=auth,
		    params={
		        'project': self.owner.parent_id,
		        'node': self.owner._id,
		        'path': path,
		        'urls': urls,
		    },
		)


	def deauthorize(self, auth):
	    """Remove user authorization from this node and log the event."""
	    # TODO: Any other addon-specific settings should be removed here.
	    node = self.owner
	    self.user_settings = None
	    self.owner.add_log(
	        action='dryad_node_deauthorized',
	        params={
	            'project': node.parent_id,
	            'node': node._id,
	        },
	        auth=auth,
	    )

	def to_json(self, user):
	    ret = super(AddonDryadNodeSettings, self).to_json(user)
	    ret.update(  {'dryad_package_doi': self.dryad_package_doi if self.dryad_package_doi else '',
	        'add_dryad_package_url': self.owner.web_url_for('set_dryad_doi'),
	        'browse_dryad_url': self.owner.web_url_for('dryad_browser'),
	        'search_dryad_url': self.owner.web_url_for('search_dryad_page') } )
	    return ret

	def update_json(self):
	    ret={
	        'dryad_package_doi': self.dryad_package_doi if self.dryad_package_doi else '',
	        'add_dryad_package_url': self.owner.web_url_for('set_dryad_doi'),
	        'browse_dryad_url': self.owner.web_url_for('dryad_browser'),
	        'search_dryad_url': self.owner.web_url_for('search_dryad_page'),
	    }
	    return ret


