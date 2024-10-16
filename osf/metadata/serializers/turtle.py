from osf.metadata.osf_gathering import OsfmapPartition
from osf.metadata.serializers import _base


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle; charset=utf-8'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.ttl'

    def serialize(self) -> str:
        _partition = self.serializer_config.get('osfmap_partition', OsfmapPartition.MAIN)
        self.basket.pls_gather(
            _partition.osfmap_for_type(self.basket.focus.rdftype),
            include_defaults=(_partition is OsfmapPartition.MAIN),
        )
        return self.basket.gathered_metadata.serialize(format='turtle')
