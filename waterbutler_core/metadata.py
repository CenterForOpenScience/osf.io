import abc


class BaseMetadata(metaclass=abc.ABCMeta):

    def __init__(self, raw):
        self.raw = raw

    def serialized(self):
        return {
            'provider': self.provider,
            'kind': self.kind,
            'name': self.name,
            'size': self.size,
            'path': self.path,
            'modified': self.modified,
            'extra': self.extra,
        }

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

    @abc.abstractproperty
    def modified(self):
        pass

    @abc.abstractproperty
    def size(self):
        pass

    @property
    def extra(self):
        return {}


class BaseRevision(metaclass=abc.ABCMeta):

    def __init__(self, raw):
        self.raw = raw

    def serialized(self):
        return {
            'provider': self.provider,
            'size': self.size,
            'modified': self.modified,
            'revision': self.revision,
            'extra': self.extra,
        }

    @abc.abstractproperty
    def provider(self):
        pass

    @abc.abstractproperty
    def modified(self):
        pass

    @abc.abstractproperty
    def size(self):
        pass

    @abc.abstractproperty
    def revision(self):
        pass

    @property
    def extra(self):
        return {}
