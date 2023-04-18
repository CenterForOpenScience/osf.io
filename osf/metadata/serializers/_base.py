import abc

from osf.metadata import gather


class MetadataSerializer(abc.ABC):
    def __init__(self, serializer_config=None):
        self.serializer_config = serializer_config or {}

    @property
    @abc.abstractmethod
    def mediatype(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def filename(self, osfguid: str):
        raise NotImplementedError

    @abc.abstractmethod
    def serialize(self, basket: gather.Basket) -> str:
        raise NotImplementedError

    # optional to implement in subclasses
    def primitivize(self, basket: gather.Basket):
        return self.serialize(basket)  # default str
