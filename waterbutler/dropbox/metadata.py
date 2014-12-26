import os

from waterbutler.core import metadata


class BaseDropboxMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder):
        super().__init__(raw)
        self.folder = folder

    @property
    def provider(self):
        return 'dropbox'

    def build_path(self, path):
        path = path.lstrip(self.folder)
        return super().build_path(path)


class DropboxFolderMetadata(BaseDropboxMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return os.path.split(self.raw['path'])[1]

    @property
    def path(self):
        return self.build_path(self.raw['path'])


class DropboxFileMetadata(BaseDropboxMetadata, metadata.BaseFileMetadata):

    @property
    def name(self):
        return os.path.split(self.raw['path'])[1]

    @property
    def path(self):
        return self.build_path(self.raw['path'])

    @property
    def size(self):
        return self.raw['bytes']

    @property
    def modified(self):
        return self.raw['modified']

    @property
    def content_type(self):
        return self.raw['mime_type']


# TODO dates!
class DropboxRevision(BaseDropboxMetadata, metadata.BaseFileRevisionMetadata):

    @property
    def size(self):
        return self.raw['bytes']

    @property
    def modified(self):
        return self.raw['modified']

    @property
    def revision(self):
        return self.raw['rev']

    @property
    def content_type(self):
        return self.raw['mime_type']

    @property
    def extra(self):
        return {
            'revisionNumber': self.raw['revision']
        }
