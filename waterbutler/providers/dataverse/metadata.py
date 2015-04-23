from waterbutler.core import metadata


class BaseDataverseMetadata(metadata.BaseMetadata):

    @property
    def provider(self):
        return 'dataverse'


class DataverseFileMetadata(BaseDataverseMetadata, metadata.BaseFileMetadata):

    def __init__(self, raw, dataset_version):
        super().__init__(raw)
        self.dataset_version = dataset_version

        # Note: If versioning by number is added, this will have to check
        # all published versions, not just 'latest-published'.
        self.has_published_version = dataset_version == 'latest-published'

    @property
    def file_id(self):
        return str(self.raw['id'])

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return self.build_path(self.file_id)

    @property
    def size(self):
        return None

    @property
    def content_type(self):
        return self.raw['contentType']

    @property
    def modified(self):
        return None

    @property
    def extra(self):
        return {
            'fileId': self.file_id,
            'datasetVersion': self.dataset_version,
            'hasPublishedVersion': self.has_published_version,
        }


class DataverseDatasetMetadata(BaseDataverseMetadata, metadata.BaseFolderMetadata):

    def __init__(self, raw, name, doi, version):
        super().__init__(raw)
        self._name = name
        self.doi = doi

        files = self.raw['files']
        self.contents = [DataverseFileMetadata(f['datafile'], version) for f in files]

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self.build_path(self.doi)


class DataverseRevision(metadata.BaseFileRevisionMetadata):

    @property
    def version_identifier(self):
        return 'version'

    @property
    def version(self):
        return self.raw

    @property
    def modified(self):
        return None
