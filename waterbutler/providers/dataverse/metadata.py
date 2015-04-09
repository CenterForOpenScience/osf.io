import abc

from waterbutler.core import metadata
from waterbutler.providers.dataverse import utils as dataverse_utils


class BaseDataverseMetadata(metadata.BaseMetadata):

    def __init__(self, raw):
        super().__init__(raw)

    @property
    def provider(self):
        return 'dataverse'


class BaseDataverseFileMetadata(BaseDataverseMetadata, metadata.BaseFileMetadata):

    def __init__(self, raw):
        super().__init__(raw)
        original_name, version = dataverse_utils.unpack_filename(self.name)
        self.original_name = original_name
        self.version = version

    @abc.abstractproperty
    def id(self):
        pass

    @property
    def path(self):
        return self.build_path(self.id)

    @property
    def size(self):
        pass

    @property
    def extra(self):
        return {
            'original': self.original_name,
            'version': self.version,
            'fileId': self.id
        }


class DataverseSwordFileMetadata(BaseDataverseFileMetadata):

    def __init__(self, raw):
        self._content = raw['content']
        self._edit_media_uri = self._content['@src']

        # Call last to ensure name has been defined by _edit_media_uri
        super().__init__(raw)

    @property
    def content_type(self):
        return self._content['@type']

    @property
    def id(self):
        return self._edit_media_uri.rsplit("/", 2)[-2]

    @property
    def name(self):
        return self._edit_media_uri.rsplit("/", 1)[-1]

    @property
    def modified(self):
        return self.raw['updated']


class DataverseNativeFileMetadata(BaseDataverseFileMetadata):

    @property
    def content_type(self):
        return self.raw['contentType']

    @property
    def id(self):
        return str(self.raw['id'])

    @property
    def name(self):
        return self.raw['name']

    @property
    def modified(self):
        pass


class DataverseDatasetMetadata(BaseDataverseMetadata, metadata.BaseFolderMetadata):

    def __init__(self, raw, name, doi, native=True):
        super().__init__(raw)
        self._name = name
        self.doi = doi

        if native:
            files = self.raw['files']
            self._entries = [DataverseNativeFileMetadata(f['datafile']) for f in files]

        else:
            entry_feed = raw['feed'].get('entry', [])
            if isinstance(entry_feed, dict):
                self._entries = [DataverseSwordFileMetadata(entry_feed)]
            else:
                self._entries = [DataverseSwordFileMetadata(e) for e in entry_feed]

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self.build_path(self.doi)

    @property
    def entries(self):
        return self._entries

    def serialized(self):
        if self._entries:
            return [e.serialized() for e in self._entries]
        return super(DataverseDatasetMetadata, self).serialized()