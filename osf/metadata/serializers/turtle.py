from osf.metadata import gather
from osf.metadata.osf_gathering import osfmap_for_type
from osf.metadata.serializers import _base


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.ttl'

    def serialize(self, basket: gather.Basket):
        basket.pls_gather(osfmap_for_type(basket.focus.rdftype))
        return basket.gathered_metadata.serialize(format='turtle')
