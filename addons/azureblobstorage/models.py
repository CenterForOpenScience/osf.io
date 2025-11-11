# -*- coding: utf-8 -*-

from osf.models.files import File, Folder, BaseFileNode
from osf.models.external import ExternalProvider

class AzureBlobStorageFileNode(BaseFileNode):
    _provider = 'azureblobstorage'


class AzureBlobStorageFolder(AzureBlobStorageFileNode, Folder):
    pass


class AzureBlobStorageFile(AzureBlobStorageFileNode, File):
    version_identifier = 'version'


class AzureBlobStorageProvider(ExternalProvider):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Azure Blob Storage'
    short_name = 'azureblobstorage'

    def __init__(self, account=None):
        super(AzureBlobStorageProvider, self).__init__()

        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )
