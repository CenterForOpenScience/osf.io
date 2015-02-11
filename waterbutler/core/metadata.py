import abc


class BaseMetadata(metaclass=abc.ABCMeta):

    def __init__(self, raw):
        self.raw = raw

    def serialized(self):
        return {
            'provider': self.provider,
            'kind': self.kind,
            'name': self.name,
            'path': self.path,
            'extra': self.extra,
        }

    def build_path(self, path):
        if not path.startswith('/'):
            path = '/' + path
        if self.kind == 'folder' and not path.endswith('/'):
            path += '/'
        return path

    @abc.abstractproperty
    def provider(self):
        pass

    @abc.abstractproperty
    def kind(self):
        pass

    @abc.abstractproperty
    def name(self):
        pass

    @abc.abstractproperty
    def path(self):
        pass

    @property
    def extra(self):
        return {}


class BaseFileMetadata(BaseMetadata):

    def serialized(self):
        return dict(super().serialized(), **{
            'contentType': self.content_type,
            'modified': self.modified,
            'size': self.size,
        })

    @property
    def kind(self):
        return 'file'

    @abc.abstractproperty
    def content_type(self):
        pass

    @abc.abstractproperty
    def modified(self):
        pass

    @abc.abstractproperty
    def size(self):
        pass


class BaseFileRevisionMetadata(metaclass=abc.ABCMeta):

    def __init__(self, raw):
        self.raw = raw

    def serialized(self):
        return {
            'extra': self.extra,
            'version': self.version,
            'modified': self.modified,
            'versionIdentifier': self.version_identifier,
        }

    @abc.abstractproperty
    def modified(self):
        pass

    @abc.abstractproperty
    def version(self):
        pass

    @abc.abstractproperty
    def version_identifier(self):
        pass

    @property
    def extra(self):
        return {}


class BaseFolderMetadata(BaseMetadata):

    @property
    def kind(self):
        return 'folder'
