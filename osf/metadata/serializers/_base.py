import abc

from osf.metadata import gather


class MetadataSerializer(abc.ABC):
    def __init__(self, basket: gather.Basket, serializer_config=None):
        self.basket = basket
        self.serializer_config = serializer_config or {}

    @property  # may be implemented with class attribute
    @abc.abstractmethod
    def mediatype(self):
        raise NotImplementedError

    @abc.abstractmethod
    def filename_for_itemid(self, itemid: str):
        raise NotImplementedError

    @abc.abstractmethod
    def serialize(self) -> str | bytes:
        raise NotImplementedError

    # optional for subclasses
    def metadata_as_dict(self) -> dict:
        raise NotImplementedError
