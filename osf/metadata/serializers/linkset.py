"""osf.metadata.serializers.signpost_linkset: FAIR signposting with osf metadata
FAIR signposting: https://signposting.org/FAIR/
definition of linkset mediatypes: https://www.rfc-editor.org/rfc/rfc9264.html
"""
from __future__ import annotations
import abc
from collections.abc import (
    Iterable,
    Iterator
)
import dataclasses

from ._base import MetadataSerializer


@dataclasses.dataclass
class SignpostLink:
    context_uri: str
    relation_uri: str
    target_uri: str
    target_attrs: Iterable[tuple(str, str)]


class BaseSignpostLinkset(MetadataSerializer, abc.ABC):
    def _each_link(self) -> Iterator[SignpostLink]:
        # author list(self.basket[DCTERMS.creator]) need to determine source of data
        # type list(self.basket[DCTERMS.type])
        # cite-as
        # describedby
        # item
        # license

        ...  # TODO yield SignpostLink(...) ...


class SignpostLinkset(BaseSignpostLinkset):
    mediatype = 'application/linkset'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.linkset'

    def serialize(self) -> str | bytes:
        """serialize a linkset for FAIR signposting
        see example https://www.rfc-editor.org/rfc/rfc9264.html#section-7.1
        FAIR signposting: https://signposting.org/FAIR/
        """
        return ''.join(map(self._serialize_link, self._each_link()))

    def _serialize_link(self, link: SignpostLink) -> str:
        ...  # TODO

class SignpostLinksetJSON(BaseSignpostLinkset):
    mediatype = 'application/linkset+json'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.linkset.json'

    def serialize(self) -> str | bytes:
        """serialize linkset json
        definition: https://www.rfc-editor.org/rfc/rfc9264.html#section-4.2
        example: https://www.rfc-editor.org/rfc/rfc9264.html#section-7.2
        """
        ...  # TODO
