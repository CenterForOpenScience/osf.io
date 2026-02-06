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
from urllib.parse import urljoin, urlsplit, urlencode, urlunsplit

import rdflib

from ._base import MetadataSerializer
from osf.metadata.osf_gathering import osfguid_from_iri
from osf.metadata.rdfutils import DOI, DCTERMS, OWL, RDF, OSF, DCAT
from website.settings import DOMAIN
from website.util import web_url_for


@dataclasses.dataclass
class SignpostLink:
    anchor_uri: str
    relation: str
    target_uri: str
    target_attrs: Iterable[tuple[str, str]] = ()


class BaseSignpostLinkset(MetadataSerializer, abc.ABC):
    def _each_link(self) -> Iterator[SignpostLink]:
        focus_iri = self.basket.focus.iri
        if self.basket.focus.rdftype == OSF.File:
            # collection (file's containing obj)
            for _collection_uri in self.basket[OSF.isContainedBy]:
                yield SignpostLink(focus_iri, 'collection', str(_collection_uri))

        # author
        for _creator_iri in self.basket[DCTERMS.creator]:
            yield SignpostLink(focus_iri, 'author', str(_creator_iri))

        # type
        if self.basket.focus.rdftype == OSF.File:
            parent_types = set(self.basket[OSF.isContainedBy / (DCTERMS.type | RDF.type)])
            for _type_iri in self.basket[DCTERMS.type | RDF.type]:
                # check the type differs from parent project / registry / preprint
                if _type_iri not in parent_types:
                    yield SignpostLink(focus_iri, 'type', str(_type_iri))
        else:
            for _type_iri in self.basket[DCTERMS.type | RDF.type]:
                yield SignpostLink(focus_iri, 'type', str(_type_iri))

        # cite-as
        yield SignpostLink(focus_iri, 'cite-as', next((
            _sameas_iri
            for _sameas_iri in self.basket[OWL.sameAs]
            if _sameas_iri.startswith(DOI)
        ), focus_iri))

        base_metadata_url = urljoin(DOMAIN, web_url_for(
            'metadata_download',  # name of a view function mapped in website/routes.py
            guid=osfguid_from_iri(self.basket.focus.iri),
        ))
        split_base_metadata_url = urlsplit(base_metadata_url)

        # describes
        yield SignpostLink(
            base_metadata_url,
            'describes',
            focus_iri,
        )

        from osf.metadata.serializers import METADATA_SERIALIZER_REGISTRY
        # describedby
        for _format_key, _serializer in METADATA_SERIALIZER_REGISTRY.items():
            _metadata_url = urlunsplit(split_base_metadata_url._replace(
                query=urlencode({'format': _format_key}),
            ))
            yield SignpostLink(
                focus_iri,
                'describedby',
                _metadata_url,
                [('type', _serializer.mediatype)]
            )

        # license
        for _license_uri in self.basket[DCTERMS.rights]:
            if not isinstance(_license_uri, rdflib.BNode):
                yield SignpostLink(focus_iri, 'license', str(_license_uri))

        # item
        for _file_iri in self.basket[OSF.contains]:
            mime_type = next(self.basket[_file_iri:DCAT.mediaType])
            yield SignpostLink(focus_iri, 'item', str(_file_iri), [('type', mime_type)])


class SignpostLinkset(BaseSignpostLinkset):
    mediatype = 'application/linkset'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata.linkset'

    def serialize(self) -> str | bytes:
        """serialize a linkset for FAIR signposting
        see example https://www.rfc-editor.org/rfc/rfc9264.html#section-7.1
        FAIR signposting: https://signposting.org/FAIR/
        """
        result = ',\n'.join(self._serialize_link(link) for link in self._each_link())
        return '{}\n'.format(result)

    def _serialize_link(self, link: SignpostLink) -> str:
        segments = [
            f'<{link.target_uri}>',
            f'rel="{link.relation}"',
            f'anchor="{link.anchor_uri}"'
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
            link_entry.update(link.target_attrs)
            grouped_links[link.anchor_uri][link.relation].append(link_entry)

        linkset = []
        for anchor, relations in grouped_links.items():
            anchor_entry = {'anchor': anchor}
            anchor_entry.update(relations)
            linkset.append(anchor_entry)

        return json.dumps({'linkset': linkset}, indent=2)
