from __future__ import unicode_literals

import logging

from modularodm import fields

from website.files import utils as files_utils
from website.files.models import OsfStorageFolder
from website.addons.osfstorage import settings
from website.addons.base import AddonNodeSettingsBase, StorageAddonBase


logger = logging.getLogger(__name__)


class OsfStorageNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    complete = True
    has_auth = True

    root_node = fields.ForeignField('StoredFileNode')

    @property
    def folder_name(self):
        return self.root_node.name

    def get_root(self):
        return self.root_node.wrapped()

    def set_root(self, new_node):
        self.root_node = new_node.get_addon('osfstorage').root_node
        self.save()
        return self.root_node.wrapped()

    def on_add(self):
        if self.root_node:
            return

        # A save is required here to both create and attach the root_node
        # When on_add is called the model that self refers to does not yet exist
        # in the database and thus odm cannot attach foreign fields to it
        self.save()
        # Note: The "root" node will always be "named" empty string
        root = OsfStorageFolder(name='', node=self.owner)
        root.save()
        self.root_node = root.stored_object
        self.save()

    def after_fork(self, node, fork, user, save=True):
        clone = self.clone()
        clone.owner = fork
        clone.save()
        if not self.root_node:
            self.on_add()

        clone.root_node = files_utils.copy_files(self.get_root(), clone.owner).stored_object
        clone.save()

        return clone, None

    def after_register(self, node, registration, user, save=True):
        clone = self.clone()
        clone.owner = registration
        clone.on_add()
        clone.save()

        return clone, None

    def serialize_waterbutler_settings(self):
        return dict(settings.WATERBUTLER_SETTINGS, **{
            'nid': self.owner._id,
            'rootId': self.root_node._id,
            'baseUrl': self.owner.api_url_for(
                'osfstorage_get_metadata',
                _absolute=True,
            )
        })

    def serialize_waterbutler_credentials(self):
        return settings.WATERBUTLER_CREDENTIALS

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for(
            'addon_view_or_download_file',
            path=metadata['path'],
            provider='osfstorage'
        )

        self.owner.add_log(
            'osf_storage_{0}'.format(action),
            auth=auth,
            params={
                'node': self.owner._id,
                'project': self.owner.parent_id,

                'path': metadata['materialized'],

                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )
