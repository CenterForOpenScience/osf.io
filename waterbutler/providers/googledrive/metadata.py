import os
from urllib import parse

from waterbutler.core import metadata

from waterbutler.providers.googledrive import utils


class BaseGoogleDriveMetadata(metadata.BaseMetadata):

    def __init__(self, raw, path):
        super().__init__(raw)
        self._path = path

    @property
    def provider(self):
        return 'googledrive'

    @property
    def path(self):
        #TODO Address this
        return os.path.join(parse.quote(str(self._path)), parse.quote(self.raw['title'], safe=''))

    @property
    def materialized_path(self):
        return os.path.join(str(self._path), self.raw['title'])

    @property
    def extra(self):
        return {'revisionId': self.raw['version']}


class GoogleDriveFolderMetadata(BaseGoogleDriveMetadata, metadata.BaseFolderMetadata):

    @property
    def id(self):
        return self.raw['id']

    @property
    def name(self):
        return self.raw['title']

    @property
    def path(self):
        return super().path + '/'

    @property
    def materialized_path(self):
        return super().materialized_path + '/'


class GoogleDriveFileMetadata(BaseGoogleDriveMetadata, metadata.BaseFileMetadata):

    @property
    def id(self):
        return self.raw['id']

    @property
    def name(self):
        title = self.raw['title']
        name, ext = os.path.splitext(title)
        if utils.is_docs_file(self.raw) and not ext:
            ext = utils.get_extension(self.raw['exportLinks'])
            title += ext
        return title

    @property
    def size(self):
        # Google docs(Docs,sheets, slides, etc)  don't have file size before they are exported
        return self.raw.get('fileSize')

    @property
    def modified(self):
        return self.raw['modifiedDate']

    @property
    def content_type(self):
        return self.raw['mimeType']

    @property
    def extra(self):
        ret = super().extra
        if utils.is_docs_file(self.raw):
            ret['downloadExt'] = utils.get_download_extension(self.raw['exportLinks'])
        return ret


class GoogleDriveRevision(metadata.BaseFileRevisionMetadata):

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def version(self):
        return self.raw['id']

    @property
    def modified(self):
        return self.raw['modifiedDate']
