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
from collections import defaultdict
import dataclasses
import json
from ._base import MetadataSerializer
from osf.metadata.rdfutils import DOI, DCTERMS, OWL, RDF, OSF
from website.settings import DOMAIN
from urllib.parse import urljoin
from website.util import web_url_for

@dataclasses.dataclass
class SignpostLink:
    context_uri: str
    relation_uri: str
    target_uri: str
    target_attrs: Iterable[tuple(str, str)]

class BaseSignpostLinkset(MetadataSerializer, abc.ABC):
    def _each_link(self) -> Iterator[SignpostLink]:
        focus_iri = self.basket.focus.iri
        for _creator_iri in self.basket[DCTERMS.creator]:
            yield SignpostLink(focus_iri, 'author', str(_creator_iri), ())

        # type
        for _type_iri in self.basket[DCTERMS.type | RDF.type]:
            yield SignpostLink(focus_iri, 'type', str(_type_iri), ())

        # cite-as
        yield SignpostLink(focus_iri, 'citeas', next((
            _sameas_iri
            for _sameas_iri in self.basket[OWL.sameAs]
            if _sameas_iri.startswith(DOI)
        ), focus_iri), ())

        _record_uri = web_url_for('metadata_download', guid=self.basket.focus.dbmodel._id)
        path = urljoin(DOMAIN, _record_uri)
        from osf.metadata.serializers import METADATA_SERIALIZER_REGISTRY
        # describedby
        for _format_key, _serializer in METADATA_SERIALIZER_REGISTRY.items():
            yield SignpostLink(
                focus_iri,
                'describedby',
                path,
                [('type', _serializer.mediatype)]
            )

        # license
        for _license_uri in self.basket[DCTERMS.rights]:
            yield SignpostLink(focus_iri, 'license', str(_license_uri), ())

        # item
        for _file_iri in self.basket[OSF.contains]:
            # add file mediatype attr? if available
            yield SignpostLink(focus_iri, 'item', str(_file_iri), ())


class SignpostLinkset(BaseSignpostLinkset):
    mediatype = 'application/linkset'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.linkset'

    def serialize(self) -> str | bytes:
        """serialize a linkset for FAIR signposting
        see example https://www.rfc-editor.org/rfc/rfc9264.html#section-7.1
        FAIR signposting: https://signposting.org/FAIR/
        """
        result = ',\n'.join(self._serialize_link(link) for link in self._each_link()) + '\n'
        return "{}\n".format(result)

    def _serialize_link(self, link: SignpostLink) -> str:
        segments = [
            f'<{link.target_uri}>',
            f'rel="{link.relation_uri}"',
            f'anchor="{link.context_uri}"'
        ]
        for key, value in link.target_attrs:
            segments.append(f'{key}="{value}"')
        return ' ; '.join(segments)

class SignpostLinksetJSON(BaseSignpostLinkset):
    mediatype = 'application/linkset+json'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.linkset.json'

    def serialize(self) -> str | bytes:
        """serialize linkset json
        definition: https://www.rfc-editor.org/rfc/rfc9264.html#section-4.2
        example: https://www.rfc-editor.org/rfc/rfc9264.html#section-7.2
        """
        grouped_links = defaultdict(lambda: defaultdict(list))

        for link in self._each_link():
            link_entry = {'href': link.target_uri}

            for key, value in link.target_attrs:
                link_entry[key] = value

            grouped_links[link.context_uri][link.relation_uri].append(link_entry)

        linkset = []
        for anchor, relations in grouped_links.items():
            anchor_entry = {'anchor': anchor}
            anchor_entry.update(relations)
            linkset.append(anchor_entry)

        return json.dumps({'linkset': linkset}, indent=2)
