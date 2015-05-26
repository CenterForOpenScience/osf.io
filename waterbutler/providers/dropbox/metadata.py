import os

from waterbutler.core import metadata


class BaseDropboxMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder):
        super().__init__(raw)
        self._folder = folder

    @property
    def provider(self):
        return 'dropbox'

    def build_path(self, path):
        # TODO write a test for this
        if path.lower().startswith(self._folder.lower()):
            path = path[len(self._folder):]
        return super().build_path(path)

    @property
    def extra(self):
        return {
            'revisionId': self.raw['rev']
        }


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

    @property
    def etag(self):
        return self.raw['rev']


# TODO dates!
class DropboxRevision(metadata.BaseFileRevisionMetadata):

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def version(self):
        return self.raw['rev']

    @property
    def modified(self):
        return self.raw['modified']
