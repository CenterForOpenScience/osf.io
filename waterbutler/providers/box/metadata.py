from waterbutler.core import metadata


class BaseBoxMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder):
        super().__init__(raw)

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
        return self.raw.get('size')

    @property
    def modified(self):
        return self.raw.get('modified_at')

    @property
    def parent(self):
        return self.raw.get('parent').get('id')

    @property
    def folder(self):
        return self.settings['folder']

    @property
    def content_type(self):
        return self.raw['type']


class BoxRevision(metadata.BaseFileRevisionMetadata):

    @property
    def size(self):
        return self.raw.get('size')

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return self.raw['name']

    @property
    def version(self):
        try:
            return self.raw['id']
        except KeyError:
            return self.raw['path'].split('/')[1]

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def path(self):
        try:
            return '/{0}/{1}'.format(self.raw['id'], self.raw['name'])
        except KeyError:
            return self.raw['path']

    @property
    def modified(self):
        return self.raw.get('modified_at')

    @property
    def revision(self):
        return self.raw['etag']

    @property
    def extra(self):
        return {
            'revisionNumber': self.raw['revision']
        }
