import os

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
        return '/' + self._path.raw_path

    @property
    def materialized_path(self):
        return str(self._path)

    @property
    def extra(self):
        return {'revisionId': self.raw['version']}


class GoogleDriveFolderMetadata(BaseGoogleDriveMetadata, metadata.BaseFolderMetadata):

    def __init__(self, raw, path):
        super().__init__(raw, path)
        self._path._is_folder = True

    @property
    def id(self):
        return self.raw['id']

    @property
    def name(self):
        return self.raw['title']


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
    def etag(self):
        return self.raw['version']

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
