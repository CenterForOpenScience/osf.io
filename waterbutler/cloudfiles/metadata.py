import os

from waterbutler.core import metadata


class CloudFilesFileMetadata(metadata.BaseMetadata):

    @property
    def provider(self):
        return 'cloudfiles'

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return os.path.split(self.raw['name'])[1]

    @property
    def path(self):
        return self.raw['name']

    @property
    def size(self):
        return self.raw['bytes']

    @property
    def modified(self):
        return self.raw['last_modified']


class CloudFilesFolderMetadata(metadata.BaseMetadata):

    @property
    def provider(self):
        return 'cloudfiles'

    @property
    def kind(self):
        return 'folder'

    @property
    def name(self):
        return self.raw['subdir']

    @property
    def path(self):
        return self.raw['subdir']

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return None
