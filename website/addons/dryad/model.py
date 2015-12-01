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
from website.addons.dryad import serializer as serializer


class AddonDryadUserSettings(AddonUserSettingsBase):
	serializer = serializer.DryadSerializer
	#TODO: Put in the user settings here:
	def delete(self, **kwargs):
		super(AddonDryadUserSettings, self).delete()
	@property
	def has_auth(self):
	    return True


class AddonDryadNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
	dryad_title = fields.StringField()
	dryad_doi = fields.StringField()
	dryad_metadata = fields.StringField()
	serializer = serializer.DryadSerializer
	complete = True
	has_auth = True

	user_settings = fields.ForeignField(
	    'addondryadusersettings', backref='authorized'
	)

	def delete(self, **kwargs):
		self.dryad_doi=None
		super(AddonDryadNodeSettings, self).delete()

	@property
	def folder_name(self):
		return self.dryad_title

	def serialize_waterbutler_credentials(self):
		return dryad_settings.WATERBUTLER_CREDENTIALS
	def serialize_waterbutler_settings(self):
		return dryad_settings.WATERBUTLER_SETTINGS
	def create_waterbutler_log(self, auth, action, metadata):
		self.owner.add_log(
				'dryad_{0}'.format(action),
				auth=auth,
				params={},
	   		)


	@property
	def has_auth(self):
	    """Whether an access token is associated with this node."""
	    return bool(self.user_settings and self.user_settings.has_auth)

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

	##### Callback overrides #####

	def before_register_message(self, node, user):
	    """Return warning text to display if user auth will be copied to a
	    registration.
	    """
	    category, title = node.project_or_component, node.title
	    if self.user_settings and self.user_settings.has_auth:
	        # TODO:
	        pass

	# backwards compatibility
	before_register = before_register_message

	def before_fork_message(self, node, user):
	    """Return warning text to display if user auth will be copied to a
	    fork.
	    """
	    # TODO
	    pass

	# backwards compatibility
	before_fork = before_fork_message

	def before_remove_contributor_message(self, node, removed):
	    """Return warning text to display if removed contributor is the user
	    who authorized the Dryad addon
	    """
	    if self.user_settings and self.user_settings.owner == removed:
	        # TODO
	        pass

	# backwards compatibility
	before_remove_contributor = before_remove_contributor_message

	def after_register(self, node, registration, user, save=True):
	    """After registering a node, copy the user settings and save the
	    chosen folder.

	    :return: A tuple of the form (cloned_settings, message)
	    """
	    clone, message = super(DryadNodeSettings, self).after_register(
	        node, registration, user, save=False
	    )
	    # Copy user_settings and add registration data
	    if self.has_auth and self.folder is not None:
	        clone.user_settings = self.user_settings
	        clone.registration_data['folder'] = self.folder
	    if save:
	        clone.save()
	    return clone, message

	def after_fork(self, node, fork, user, save=True):
	    """After forking, copy user settings if the user is the one who authorized
	    the addon.

	    :return: A tuple of the form (cloned_settings, message)
	    """
	    clone, _ = super(DryadNodeSettings, self).after_fork(
	        node=node, fork=fork, user=user, save=False
	    )

	    if self.user_settings and self.user_settings.owner == user:
	        clone.user_settings = self.user_settings
	        message = 'Dryad Service authorization copied to fork.'
	    else:
	        message = ('Dryad Service authorization not copied to fork. You may '
	                    'authorize this fork on the <a href="{url}">Settings</a>'
	                    'page.').format(
	                    url=fork.web_url_for('node_setting'))
	    if save:
	        clone.save()
	    return clone, message

	def after_remove_contributor(self, node, removed):
	    """If the removed contributor was the user who authorized the Dryad
	    addon, remove the auth credentials from this node.
	    Return the message text that will be displayed to the user.
	    """
	    if self.user_settings and self.user_settings.owner == removed:
	        self.user_settings = None
	        self.save()
	        name = removed.fullname
	        url = node.web_url_for('node_setting')
	        return ('Because the Dryad Service add-on for this project was authenticated'
	                'by {name}, authentication information has been deleted. You '
	                'can re-authenticate on the <a href="{url}">Settings</a> page'
	                ).format(**locals())
