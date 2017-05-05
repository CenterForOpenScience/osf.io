from website.files.models.base import File, Folder, FileNode

__all__ = ('AzureBlobStorageFile', 'AzureBlobStorageFolder', 'AzureBlobStorageFileNode')


class AzureBlobStorageFileNode(FileNode):
    provider = 'azureblobstorage'


class AzureBlobStorageFolder(AzureBlobStorageFileNode, Folder):
    pass


class AzureBlobStorageFile(AzureBlobStorageFileNode, File):
    version_identifier = 'version'
