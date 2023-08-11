from osf.metadata.osf_gathering import osfmap_for_type
from osf.metadata.serializers import _base


TURTLEBLOCK_DELIMITER = '\n\n'
PREFIXBLOCK_START = '@prefix'

def _stabilize_turtle(turtle: str, focus_iri: str):
    # rdflib's turtle serializer:
    #   sorts keys alphabetically (by unicode string comparison)
    #   may emit blocks in any order
    # this function sorts those blocks for a stable serialization.
    turtleblocks = (
        turtleblock
        for turtleblock in turtle.split(TURTLEBLOCK_DELIMITER)
        if turtleblock  # skip empty blocks
    )
    sorted_turtleblocks = sorted(
        (turtleblock.strip() for turtleblock in turtleblocks),
        key=_get_turtleblock_sortkey(focus_iri),
    )
    return TURTLEBLOCK_DELIMITER.join(sorted_turtleblocks)


def _get_turtleblock_sortkey(focus_iri: str):
    focusblock_start = f'<{focus_iri}> '

    def turtleblock_sortkey(block):
        return (
            (not block.startswith(PREFIXBLOCK_START)),  # prefix block first,
            (not block.startswith(focusblock_start)),   # then focus block,
            -len(block),                                # then longest to shortest,
            block,                                      # breaking ties by string comparison.
        )
    return turtleblock_sortkey


class TurtleMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/turtle'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.ttl'

    def serialize(self) -> str:
        self.basket.pls_gather(osfmap_for_type(self.basket.focus.rdftype))
        return _stabilize_turtle(
            turtle=(
                self.basket.gathered_metadata
                .serialize(format='turtle')
                .decode()
            ),
            focus_iri=self.basket.focus.iri,
        )
