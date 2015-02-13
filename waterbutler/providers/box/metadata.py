import os

from waterbutler.core import metadata


class BaseBoxMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder):
        super().__init__(raw)
        self._folder = folder

    @property
    def provider(self):
        return 'box'


class BoxFolderMetadata(BaseBoxMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return '/{}/'.format(self.raw['id'])

    @property
    def content_type(self):
        return self.raw['type']


class BoxFileMetadata(BaseBoxMetadata, metadata.BaseFileMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return '/{0}/{1}'.format(self.raw['id'], self.raw['name'])

    @property
    def size(self):
        try:
            return self.raw['size']
        except KeyError:
            return None

    @property
    def modified(self):
        try:
            return self.raw['modified_at']
        except KeyError:
            return None 

    @property
    def parent(self):
        try:
            return self.raw['parent']['id']
        except KeyError:
            return None 

    @property
    def folder(self):
        return self.settings['folder']

    @property
    def content_type(self):
        return self.raw['type']


# TODO dates!
class BoxRevision(BaseBoxMetadata, metadata.BaseFileRevisionMetadata):

    @property
    def size(self):
        return self.raw['size']

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return self.raw['name'] 

    @property
    def version(self):
        return self.raw['revision']

    @property
    def version_identifier(self):
        return self.raw['id']

    @property
    def path(self):
        return '/{0}/{1}'.format(self.raw['id'], self.raw['name'])

    @property
    def modified(self):
        return self.raw['modified_at']

    @property
    def revision(self):
        return self.raw['etag']

    @property
    def extra(self):
        return {
            'revisionNumber': self.raw['revision']
        }
