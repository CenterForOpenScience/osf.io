from osf.metadata.osf_gathering import osfmap_for_type, osfmap_supplement_for_type
from osf.metadata.serializers import _base


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle; charset=utf-8'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.ttl'

    def serialize(self) -> str:
        if self.serializer_config.get('is_supplementary', False):
            self.basket.pls_gather(
                osfmap_supplement_for_type(self.basket.focus.rdftype),
                include_defaults=False,
            )
        else:
            self.basket.pls_gather(osfmap_for_type(self.basket.focus.rdftype))
        return self.basket.gathered_metadata.serialize(format='turtle')
