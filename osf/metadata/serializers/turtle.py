from osf.metadata import gather
from osf.metadata.osf_gathering import osfmap_for_type
from osf.metadata.serializers import _base


TURTLEBLOCK_DELIMITER = b'\n\n'
PREFIXBLOCK_START = b'@prefix'


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.ttl'

    def serialize(self, basket: gather.Basket):
        basket.pls_gather(osfmap_for_type(basket.focus.rdftype))
        # rdflib's turtle serializer:
        #   sorts keys alphabetically (by unicode string comparison)
        #   may emit blocks in any order
        turtleblocks = (
            turtleblock
            for turtleblock in (
                basket.gathered_metadata
                .serialize(format='turtle')
                .split(TURTLEBLOCK_DELIMITER)
            )
            if turtleblock  # skip empty blocks
        )
        focusblock_start = f'<{basket.focus.iri}> '.encode()

        def turtleblock_sortkey(block):
            return (
                (not block.startswith(PREFIXBLOCK_START)),  # prefix block first,
                (not block.startswith(focusblock_start)),   # then focus block,
                -len(block),                                # then longest to shortest,
                block,                                      # breaking ties by string comparison.
            )

        sorted_turtleblocks = sorted(
            (turtleblock.strip() for turtleblock in turtleblocks),
            key=turtleblock_sortkey,
        )
        return TURTLEBLOCK_DELIMITER.join(sorted_turtleblocks)
