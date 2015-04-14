from waterbutler.core import metadata
from waterbutler.providers.dataverse import utils as dataverse_utils


class BaseDataverseMetadata(metadata.BaseMetadata):

    def __init__(self, raw):
        super().__init__(raw)

    @property
    def provider(self):
        return 'dataverse'


class DataverseFileMetadata(BaseDataverseMetadata, metadata.BaseFileMetadata):

    def __init__(self, raw):
        super().__init__(raw)
        original_name, version = dataverse_utils.unpack_filename(self.name)
        self.original_name = original_name
        self.version = version

    @property
    def id(self):
        return str(self.raw['id'])

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return self.build_path(self.id)

    @property
    def size(self):
        pass

    @property
    def content_type(self):
        return self.raw['contentType']

    @property
    def modified(self):
        pass

    @property
    def extra(self):
        return {
            'original': self.original_name,
            'version': self.version,
            'fileId': self.id
        }


class DataverseDatasetMetadata(BaseDataverseMetadata, metadata.BaseFolderMetadata):

    def __init__(self, raw, name, doi):
        super().__init__(raw)
        self._name = name
        self.doi = doi

        files = self.raw['files']
        self._entries = [DataverseFileMetadata(f['datafile']) for f in files]


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