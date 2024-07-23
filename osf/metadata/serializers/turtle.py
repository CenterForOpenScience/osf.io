from osf.metadata.osf_gathering import osfmap_for_type
from osf.metadata.serializers import _base


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle; charset=utf-8'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.ttl'

    def serialize(self) -> str:
        self.basket.pls_gather(osfmap_for_type(self.basket.focus.rdftype))
        return self.basket.gathered_metadata.serialize(format='turtle')
