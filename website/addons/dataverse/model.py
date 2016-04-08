# -*- coding: utf-8 -*-
from time import sleep
import requests
import httplib as http

from modularodm import fields

from framework.auth.decorators import Auth
from framework.exceptions import HTTPError

from website.addons.base import (
    AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase, exceptions,
)
from website.addons.base import StorageAddonBase
from website.util import waterbutler_url_for

from website.addons.dataverse.client import connect_from_settings_or_401
from website.addons.dataverse import serializer
from website.addons.dataverse.provider import DataverseProvider
from website.addons.dataverse.utils import DataverseNodeLogger


class AddonDataverseUserSettings(AddonOAuthUserSettingsBase):

    oauth_provider = DataverseProvider
    serializer = serializer.DataverseSerializer

    # Legacy Fields
    api_token = fields.StringField()
    dataverse_username = fields.StringField()
    encrypted_password = fields.StringField()


class AddonDataverseNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = DataverseProvider
    serializer = serializer.DataverseSerializer

    dataverse_alias = fields.StringField()
    dataverse = fields.StringField()
    dataset_doi = fields.StringField()
    _dataset_id = fields.StringField()
    dataset = fields.StringField()

    # Legacy fields
    study_hdl = fields.StringField()    # Now dataset_doi
    study = fields.StringField()        # Now dataset

    # Legacy settings objects won't have IDs
    @property
    def folder_name(self):
        return self.dataset

    @property
    def dataset_id(self):
        if self._dataset_id is None:
            connection = connect_from_settings_or_401(self.user_settings)
            dataverse = connection.get_dataverse(self.dataverse_alias)
            dataset = dataverse.get_dataset_by_doi(self.dataset_doi)
            self._dataset_id = dataset.id
            self.save()
        return self._dataset_id

    @dataset_id.setter
    def dataset_id(self, value):
        self._dataset_id = value

    @property
    def complete(self):
        return bool(self.has_auth and self.dataset_doi is not None)

    @property
    def folder_id(self):
        return self.dataset_id

    @property
    def folder_path(self):
        pass

    @property
    def nodelogger(self):
        # TODO: Use this for all log actions
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        return DataverseNodeLogger(
            node=self.owner,
            auth=auth
        )

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        kwargs = dict(
            provider=self.config.short_name,
            path=filenode.get('path', ''),
            node=self.owner,
            user=user,
            view_only=True,
        )
        if cookie:
            kwargs['cookie'] = cookie
        if version:
            kwargs['version'] = version
        metadata_url = waterbutler_url_for(
            'metadata',
            **kwargs
        )
        res = requests.get(metadata_url)
        if res.status_code != 200:
            # The Dataverse API returns a 404 if the dataset has no published files
            if res.status_code == http.NOT_FOUND and version == 'latest-published':
                return []
            raise HTTPError(res.status_code, data={
                'error': res.json(),
            })
        # TODO: better throttling?
        sleep(1.0 / 5.0)
        return res.json().get('data', [])

    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(AddonDataverseNodeSettings, self).delete(save)

    def clear_settings(self):
        """Clear selected Dataverse and dataset"""
        self.dataverse_alias = None
        self.dataverse = None
        self.dataset_doi = None
        self.dataset_id = None
        self.dataset = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            self.owner.add_log(
                action='dataverse_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.oauth_secret}

    def serialize_waterbutler_settings(self):
        return {
            'host': self.external_account.oauth_key,
            'doi': self.dataset_doi,
            'id': self.dataset_id,
            'name': self.dataset,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='dataverse')
        self.owner.add_log(
            'dataverse_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.dataset,
                'filename': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    ##### Callback overrides #####

    # Note: Registering Dataverse content is disabled for now
    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of Dataverse add-ons cannot be registered at this time; '
                u'the Dataverse dataset linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(**locals())

    # backwards compatibility
    before_register = before_register_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Dataverse addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return ('The Dataverse add-on for this {category} is authenticated by {name}. '
                    'Removing this user will also remove write access to Dataverse '
                    'unless another contributor re-authenticates the add-on.'
                    ).format(**locals())

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    # Note: Registering Dataverse content is disabled for now
    # def after_register(self, node, registration, user, save=True):
    #     """After registering a node, copy the user settings and save the
    #     chosen folder.
    #
    #     :return: A tuple of the form (cloned_settings, message)
    #     """
    #     clone, message = super(AddonDataverseNodeSettings, self).after_register(
    #         node, registration, user, save=False
    #     )
    #     # Copy user_settings and add registration data
    #     if self.has_auth and self.folder is not None:
    #         clone.user_settings = self.user_settings
    #         clone.registration_data['folder'] = self.folder
    #     if save:
    #         clone.save()
    #     return clone, message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(AddonDataverseNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'Dataverse authorization copied to forked {cat}.'
            ).format(
                cat=fork.project_or_component
            )
        else:
            message = (
                'Dataverse authorization not copied to forked {cat}. You may '
                'authorize this fork on the <u><a href="{url}">Settings</a></u> '
                'page.'
            ).format(
                url=fork.web_url_for('node_setting'),
                cat=fork.project_or_component
            )
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed, auth=None):
        """If the removed contributor was the user who authorized the Dataverse
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()

            message = (
                u'Because the Dataverse add-on for {category} "{title}" was authenticated '
                u'by {user}, authentication information has been deleted.'
            ).format(
                category=node.category_display,
                title=node.title,
                user=removed.fullname
            )

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <u><a href="{url}">Settings</a></u> page.'
                ).format(url=url)
            #
            return message

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
