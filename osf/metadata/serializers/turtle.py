from osf.metadata import gather
from osf.metadata.serializers import _base


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.ttl'

    def serialize(self, basket: gather.Basket):
        return basket.gathered_metadata.serialize(format='turtle')
