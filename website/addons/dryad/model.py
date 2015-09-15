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
from website.addons.base import GuidFile
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.dryad import utils
from website.addons.dryad.api import Dryad
from website.addons.dryad import settings as dryad_settings



class DryadGuidFile(GuidFile):
    __indices__ = [
        {
            'key_or_list': [
                ('node', pymongo.ASCENDING),
                ('path', pymongo.ASCENDING),
            ],
            'unique': True,
        }
    ]

    path = fields.StringField(index=True)    


    def maybe_set_version(self, **kwargs):
        # branches are always required for file requests, if not specified
        # file server will assume default branch. e.g. master or develop
        if not kwargs.get('ref'):
            kwargs['ref'] = kwargs.pop('branch', None)
        super(DryadGuidFile, self).maybe_set_version(**kwargs)

    @property
    def waterbutler_path(self):
        return self.path

    @property
    def provider(self):
        return 'dryad'

    @property
    def version_identifier(self):
        return 'ref'

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['fileSha']

    @property
    def name(self):
        return os.path.split(self.path)[1]

    @property
    def external_url(self):
        return self._metadata_cache['extra']['webView']

    @property
    def extra(self):
        if not self._metadata_cache:
            return {}

        return {
            'sha': self._metadata_cache['extra']['fileSha'],
        }

    def _exception_from_response(self, response):
        try:
            if response.json()['errors'][0]['code'] == 'too_large':
                raise TooBigToRenderError(self)
        except (KeyError, IndexError):
            pass

        super(dryadGuidFile, self)._exception_from_response(response)




class AddonDryadUserSettings(AddonUserSettingsBase):

    @property
    def has_auth(self):
        return True


    def delete(self, save=False):
        #Add in clear here
        super(AddonDryadUserSettings, self).delete(save=save)


class AddonDryadNodeSettings(StorageAddonBase, AddonNodeSettingsBase):


    user_settings = fields.ForeignField(
        'addondryadusersettings', backref='authorized'
    )

    registration_data = fields.DictionaryField()


    @property
    def has_auth(self):
        return bool(self.user_settings and self.user_settings.has_auth)

    @property
    def complete(self):
        return self.has_auth

    def find_or_create_file_guid(self, path):
        return DryadGuidFile.get_or_create(node=self.owner, path=path)

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.owner.add_log(
            action='dryad_node_authorized',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
            },
            auth=Auth(user_settings.owner),
        )
        if save:
            self.save()

    def deauthorize(self, auth=None, log=True, save=False):
        self.delete_hook(save=False)
        self.user, self.repo, self.user_settings = None, None, None
        if log:
            self.owner.add_log(
                action='dryad_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )
        if save:
            self.save()

    def delete(self, save=False):
        super(AddonDryadNodeSettings, self).delete(save=False)
        self.deauthorize(save=False, log=False)
        if save:
            self.save()


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
            message = 'Dryad authorization copied to fork.'
        else:
            message = ('Dryad authorization not copied to fork. You may '
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
            return ('Because the Dryad add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())
