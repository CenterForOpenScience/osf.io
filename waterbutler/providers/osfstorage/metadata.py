import os

from waterbutler.core import metadata

class BaseOsfStorageMetadata:
    @property
    def provider(self):
        return 'osfstorage'


class OsfStorageFileMetadata(BaseOsfStorageMetadata, metadata.BaseFileMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return os.path.join(self.raw['path'], self.name)

    @property
    def modified(self):
        return self.raw.get('modified')

    @property
    def size(self):
        return self.raw.get('size')

    @property
    def content_type(self):
        return None


class OsfStorageFolderMetadata(BaseOsfStorageMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return os.path.join(self.raw['path'], self.name)
