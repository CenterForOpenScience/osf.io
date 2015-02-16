import os

from waterbutler.core import metadata


class BaseGoogleDriveMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder):
        super().__init__(raw)
        self._folder = folder

    @property
    def provider(self):
        return 'gdrive'

    def build_path(self, path):
        # TODO write a test for this
        if path.lower().startswith(self._folder.lower()):
            path = path[len(self._folder):]
        return super().build_path(path)


class GoogleDriveFolderMetadata(BaseGoogleDriveMetadata, metadata.BaseFolderMetadata):


    @property
    def id(self):
        return self.raw['id']

    @property
    def name(self):
        return self.raw['title']

    @property
    def path(self):
        return'/{0}/{1}/{2}'.format(self.raw['id'], self.raw['title'], self.raw['path'])


class GoogleDriveFileMetadata(BaseGoogleDriveMetadata, metadata.BaseFileMetadata):

    @property
    def id(self):
        return self.raw['id']

    @property
    def name(self):
        return self.raw['title']

    @property
    def path(self):
        return '/{0}/{1}/{2}'.format(self.raw['id'], self.raw['title'], self.raw['path'])

    @property
    def size(self):
        # Google docs(Docs,sheets, slides, etc)  don't have file size before they are exported
        try:
            return self.raw['fileSize']
        except KeyError:
            return '0'

    @property
    def modified(self):
        #return self.raw['modified']
        pass
    @property
    def content_type(self):
        return self.raw['mimeType']


# TODO dates!
class GoogleDriveRevision(BaseGoogleDriveMetadata, metadata.BaseFileRevisionMetadata):

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
