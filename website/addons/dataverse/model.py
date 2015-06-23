# -*- coding: utf-8 -*-
from time import sleep
import requests
import urlparse
import httplib as http

import pymongo
from modularodm import fields

from framework.auth.core import _get_current_user
from framework.auth.decorators import Auth
from framework.exceptions import HTTPError

from website.security import encrypt, decrypt

from website.addons.base import (
    AddonNodeSettingsBase, AddonUserSettingsBase, GuidFile, exceptions,
)
from website.addons.base import StorageAddonBase
from website.util import waterbutler_url_for

from website.addons.dataverse.client import connect_from_settings_or_401
from website.addons.dataverse.settings import HOST


class DataverseFile(GuidFile):

    __indices__ = [
        {
            'key_or_list': [
                ('node', pymongo.ASCENDING),
                ('file_id', pymongo.ASCENDING),
            ],
            'unique': True,
        }
    ]

    file_id = fields.StringField(required=True, index=True)

    @property
    def waterbutler_path(self):
        return '/' + self.file_id

    @property
    def provider(self):
        return 'dataverse'

    @property
    def version_identifier(self):
        return 'version'

    @property
    def unique_identifier(self):
        return self.file_id

    def enrich(self, save=True):
        super(DataverseFile, self).enrich(save)

        # Check permissions
        user = _get_current_user()
        if not user or not self.node.can_edit(user=user):
            try:
                # Users without edit permission can only see published files
                if not self._metadata_cache['extra']['hasPublishedVersion']:
                    raise exceptions.FileDoesntExistError
            except (KeyError, IndexError):
                pass


class AddonDataverseUserSettings(AddonUserSettingsBase):

    api_token = fields.StringField()

    # Legacy Fields
    dataverse_username = fields.StringField()
    encrypted_password = fields.StringField()

    @property
    def has_auth(self):
        return bool(self.api_token)

    @property
    def dataverse_password(self):
        if self.encrypted_password is None:
            return None

        return decrypt(self.encrypted_password)

    @dataverse_password.setter
    def dataverse_password(self, value):
        if value is None:
            self.encrypted_password = None
            return

        self.encrypted_password = encrypt(value)

    def delete(self, save=True):
        self.clear()
        super(AddonDataverseUserSettings, self).delete(save)

    def clear(self):
        """Clear settings and deauthorize any associated nodes.

        :param bool delete: Indicates if the settings should be deleted.
        """
        self.api_token = None
        for node_settings in self.addondataversenodesettings__authorized:
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()
        return self


class AddonDataverseNodeSettings(StorageAddonBase, AddonNodeSettingsBase):

    dataverse_alias = fields.StringField()
    dataverse = fields.StringField()
    dataset_doi = fields.StringField()
    _dataset_id = fields.StringField()
    dataset = fields.StringField()

    # Legacy fields
    study_hdl = fields.StringField()    # Now dataset_doi
    study = fields.StringField()        # Now dataset

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

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
    def has_auth(self):
        """Whether a dataverse account is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

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

    def find_or_create_file_guid(self, path):
        file_id = path.strip('/') if path else ''
        return DataverseFile.get_or_create(node=self.owner, file_id=file_id)

    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(AddonDataverseNodeSettings, self).delete(save)

    def set_user_auth(self, user_settings):
        node = self.owner
        self.user_settings = user_settings
        node.add_log(
            action='dataverse_node_authorized',
            auth=Auth(user_settings.owner),
            params={
                'project': node.parent_id,
                'node': node._primary_key,
            }
        )

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.dataverse_alias = None
        self.dataverse = None
        self.dataset_doi = None
        self.dataset_id = None
        self.dataset = None
        self.user_settings = None

        if add_log:
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
        return {'token': self.user_settings.api_token}

    def serialize_waterbutler_settings(self):
        return {
            'host': HOST,
            'doi': self.dataset_doi,
            'id': self.dataset_id,
            'name': self.dataset,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']
        if 'name' in metadata:
            name = metadata['name']
        else:
            query_string = urlparse.urlparse(metadata['full_path']).query
            name = urlparse.parse_qs(query_string).get('name')

        url = self.owner.web_url_for('addon_view_or_download_file', path=path, provider='dataverse')
        self.owner.add_log(
            'dataverse_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.dataset,
                'filename': name,
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

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return ('Because you have authorized the Dataverse add-on for this '
                '{category}, forking it will also transfer your authentication '
                'to the forked {category}.').format(category=category)

        else:
            return ('Because the Dataverse add-on has been authorized by a different '
                    'user, forking it will not transfer authentication to the forked '
                    '{category}.').format(category=category)

    # backwards compatibility
    before_fork = before_fork_message

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
                'authorize this fork on the <a href="{url}">Settings</a> '
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
                    u' You can re-authenticate on the <a href="{url}">Settings</a> page.'
                ).format(url=url)
            #
            return message

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
