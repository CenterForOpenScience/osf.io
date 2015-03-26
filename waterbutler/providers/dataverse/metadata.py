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
        self._content = raw['content']
        self._edit_media_uri = self._content['@src']

        original_name, version = dataverse_utils.unpack_filename(self.name)
        self.original_name = original_name
        self.version = version
        
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
    def path(self):
        return self.build_path(self.id)

    @property
    def modified(self):
        return self.raw['updated']

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


class DataverseDatasetMetadata(BaseDataverseMetadata, metadata.BaseFolderMetadata):
    
    def __init__(self, raw, state):
        super().__init__(raw)

        # Filter out unpublished datasets
        if state == 'published':
            dataset_state = next(
                item for item in raw['feed']['category']
                if item['@term'] == 'latestVersionState'
            )['#text'].lower()
            if dataset_state == 'draft':
                self._entries = []
                return

        entry_feed = raw['feed'].get('entry') or []
        if isinstance(entry_feed, dict):
            self._entries = [DataverseFileMetadata(entry_feed)]
        else:
            self._entries = [DataverseFileMetadata(e) for e in entry_feed]

    @property
    def id(self):
        return self.raw['feed']['id'].rsplit('/study/', 1)[-1]

    @property
    def name(self):
        return self.raw['feed']['title']['#text']

    @property
    def path(self):
        return self.build_path(self.id)

    @property
    def entries(self):
        return self._entries

    def serialized(self):
        if self._entries:
            return [e.serialized() for e in self._entries]
        return super(DataverseDatasetMetadata, self).serialized()