import os

from waterbutler.core import metadata

class BaseDataverseMetadata(metadata.BaseMetadata):

    def __init__(self, raw):
        super().__init__(raw)

    @property
    def provider(self):
        return 'dataverse'

    # TODO why?
    @property
    def kind(self):
        pass

    def build_path(self, path):
        return path


class DataverseFileMetadata(BaseDataverseMetadata):
    
    def __init__(self, raw):
        super().__init__(raw)
        
        content = raw['content']
        
        self._raw = raw
        self._content_type = content['@type']
        self._edit_media_uri = raw['id']
        self._updated = raw['updated']
        
    @property
    def content_type(self):
        return self._content_type

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
    def updated(self):
        return self._updated


class DataverseDatasetMetadata(BaseDataverseMetadata):
    
    def __init__(self, raw):
        super().__init__(raw)

        feed = raw['feed']
        
        self._id = feed['id']
        self._title = feed['title']['#text']
        feed = feed.get('entry') or []
        if isinstance(feed, dict):
            self._entries = [DataverseFileMetadata(feed)]
        else:
            self._entries = [DataverseFileMetadata(e) for e in feed]
        
    @property
    def title(self):
        return self._title

    # TODO remove redundant
    @property
    def name(self):
        return self.title

    @property
    def path(self):
        return self.build_path(self._id)

    @property
    def entries(self):
        return self._entries

    def serialized(self):
        if self._entries:
            return [e.serialized() for e in self._entries]
        return super(DataverseDatasetMetadata, self).serialized()