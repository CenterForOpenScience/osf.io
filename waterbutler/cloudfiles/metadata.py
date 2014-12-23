import os

from waterbutler.core import metadata


class CloudFilesHeaderMetadata(metadata.BaseFileMetadata):

    def __init__(self, raw, path):
        super().__init__(raw)
        self._path = path

    @property
    def provider(self):
        return 'cloudfiles'

    @property
    def name(self):
        return os.path.split(self._path)[1]

    @property
    def path(self):
        return self._path

    @property
    def size(self):
        return int(self.raw['Content-Length'])

    @property
    def modified(self):
        return self.raw['Last-Modified']

    @property
    def content_type(self):
        return self.raw['Content-Type']


class CloudFilesFileMetadata(metadata.BaseFileMetadata):

    @property
    def provider(self):
        return 'cloudfiles'

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

    @property
    def content_type(self):
        return self.raw['content_type']


class CloudFilesFolderMetadata(metadata.BaseFolderMetadata):

    @property
    def provider(self):
        return 'cloudfiles'

    @property
    def name(self):
        return self.raw['subdir'].rstrip('/').split('/')[-1]

    @property
    def path(self):
        return self.raw['subdir']
