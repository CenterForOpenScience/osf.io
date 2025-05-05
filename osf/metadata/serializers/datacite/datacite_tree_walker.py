import datetime
import itertools
import logging
import re
import typing

import rdflib

from framework import sentry
from osf.exceptions import MetadataSerializationError
from osf.external.gravy_valet.request_helpers import get_verified_links
from osf.metadata import gather
from osf.metadata.rdfutils import (
    RDF,
    DCTERMS,
    DOI,
    DxDOI,
    FOAF,
    ORCID,
    OSF,
    ROR,
    SKOS,
    DATACITE,
    smells_like_iri,
    without_namespace,
)


logger = logging.getLogger(__name__)


RELATED_IDENTIFIER_TYPE_MAP = {
    DCTERMS.hasPart: 'HasPart',
    DCTERMS.hasVersion: 'HasVersion',
    DCTERMS.isPartOf: 'IsPartOf',
    DCTERMS.isVersionOf: 'IsVersionOf',
    DCTERMS.references: 'References',
    DCTERMS.relation: 'References',
    OSF.archivedAt: 'IsIdenticalTo',
    OSF.hasRoot: 'IsPartOf',
    OSF.isContainedBy: 'IsPartOf',
    OSF.supplements: 'IsSupplementTo',
    OSF.isSupplementedBy: 'IsSupplementedBy',
    OSF.hasDataResource: 'References',
    OSF.hasAnalyticCodeResource: 'References',
    OSF.hasMaterialsResource: 'References',
    OSF.hasPapersResource: 'References',
    OSF.hasPreregisteredAnalysisPlan: 'References',
    OSF.hasPreregisteredStudyDesign: 'References',
    OSF.hasSupplementalResource: 'References',
}
DATE_TYPE_MAP = {
    DCTERMS.created: 'Created',
    DCTERMS.modified: 'Updated',
    DCTERMS.dateSubmitted: 'Submitted',
    DCTERMS.dateAccepted: 'Valid',
    DCTERMS.available: 'Available',
    DCTERMS.date: 'Other',
    OSF.withdrawn: 'Withdrawn',
}
PUBLICATION_YEAR_FALLBACK_ORDER = (
    DCTERMS.available,
    DCTERMS.dateAccepted,
    DCTERMS.created,
    DCTERMS.modified,
)
CONTRIBUTOR_TYPE_MAP = {
    # TODO: contributor roles
    # DCTERMS.contributor: 'ProjectMember',
    OSF.hostingInstitution: 'HostingInstitution',
}


class DataciteTreeWalker:
    '''for walking in the shape of the DataCite XML Schema thru a gather.Basket of metadata

    conforms with the structure in https://schema.datacite.org/meta/kernel-4.5/metadata.xsd
    but avoids assuming XML -- a callback function handles visiting tree branches along the
    walk to serialize the metadata (or whatever you're doing in the shape of DataCite XML),
    but the walker merely walks by.
    '''

    def __init__(self, basket: gather.Basket, root: typing.Any, visit_tree_branch: typing.Callable):
        '''
        @param basket: an instance of osf.metadata.gather.Basket (a basket of metadata)
        @param visit_tree_branch: function with expected signature:
             def visit_tree_branch(
                 parent: typing.Any,
                 child_name: str,
                 *,
                 text: str = None,
                 attrib: dict = None,
                 is_list: bool = False,
             ) -> typing.Any
            (return value will be passed as `parent` to visit its child branches)
        '''
        self.basket = basket
        self.root = root
        self.visit = visit_tree_branch

    def walk(self, doi_override=None):
        # root only passed to self._walk, not otherwise touched
        self._visit_identifier(self.root, doi_override=doi_override)
        self._visit_creators(self.root, self.basket.focus.iri)
        self._visit_titles(self.root, self.basket.focus.iri)
        self._visit_publisher(self.root, self.basket.focus.iri)
        self._visit_publication_year(self.root, self.basket.focus.iri)
        self._visit_subjects(self.root)
        self._visit_contributors(self.root, self.basket.focus.iri)
        self._visit_dates(self.root)
        self._visit_language(self.root)
        self._visit_resource_type(self.root)
        self._visit_alternate_identifiers(self.root)
        self._visit_format(self.root)
        self._visit_rights(self.root)
        self._visit_descriptions(self.root, self.basket.focus.iri)
        self._visit_funding_references(self.root)
        self._visit_related_and_verified_links(self.root)

    def _visit_identifier(self, parent_el, *, doi_override=None):
        if doi_override is None:
            identifier = self._get_one_identifier(self.basket.focus.iri)
            identifier_type, identifier_value = self._identifier_type_and_value(identifier)
        else:
            identifier_type, identifier_value = ('DOI', doi_override)
        if identifier_value:
            self.visit(parent_el, 'identifier', text=identifier_value, attrib={
                'identifierType': identifier_type,
            })

    def _visit_creators(self, parent_el, focus_iri):
        creator_iris = set(self.basket[focus_iri:DCTERMS.creator])
        if (not creator_iris) and ((focus_iri, RDF.type, OSF.File) in self.basket):
            creator_iris.update(self.basket[focus_iri:OSF.hasFileVersion / DCTERMS.creator])
        if not creator_iris:
            creator_iris.update(self.basket[focus_iri:OSF.isContainedBy / DCTERMS.creator])
        if not creator_iris:
            creator_iris.update(self.basket[focus_iri:DCTERMS.isPartOf / DCTERMS.creator])
        if not creator_iris:
            creator_iris.update(self.basket[focus_iri:DCTERMS.contributor])
        if not creator_iris:
            creator_iris.update(self.basket[focus_iri:OSF.isContainedBy / DCTERMS.contributor])
        if not creator_iris:
            creator_iris.update(self.basket[focus_iri:DCTERMS.isPartOf / DCTERMS.contributor])
        if not creator_iris:
            raise ValueError(f'gathered no creators or contributors around {focus_iri}')
        creators_el = self.visit(parent_el, 'creators', is_list=True)
        for creator_iri in creator_iris:  # TODO: "priority order"
            creator_el = self.visit(creators_el, 'creator')
            for name in self.basket[creator_iri:FOAF.name]:
                self.visit(creator_el, 'creatorName', text=name, attrib={
                    'nameType': self._get_name_type(creator_iri),
                })
            self._visit_name_identifiers(creator_el, creator_iri)
            self._visit_affiliations(creator_el, creator_iri)

    def _identifier_type_and_value(self, identifier: str):
        if identifier.startswith(DOI):
            return ('DOI', without_namespace(identifier, DOI))
        elif identifier.startswith(DxDOI):
            return ('DOI', without_namespace(identifier, DxDOI))
        elif identifier.startswith(ROR):
            return ('ROR', identifier)  # ROR keeps the full IRI
        elif identifier.startswith(ORCID):
            return ('ORCID', without_namespace(identifier, ORCID))
        elif smells_like_iri(identifier):
            return ('URL', identifier)
        logger.warning('skipping non-IRI-shaped identifier "%s"', identifier)

    def _funder_identifier_type(self, identifier: str):
        if identifier.startswith(DxDOI) or identifier.startswith(DOI):
            return 'Crossref Funder ID'
        if identifier.startswith(ROR):
            return 'ROR'
        return 'Other'

    def _get_name_type(self, agent_iri):
        if (agent_iri, RDF.type, FOAF.Person) in self.basket:
            return 'Personal'
        if (agent_iri, RDF.type, FOAF.Organization) in self.basket:
            return 'Organizational'
        raise MetadataSerializationError(f'could not determine nameType for {agent_iri}')

    def _visit_alternate_identifiers(self, parent_el):
        alt_ids_el = self.visit(parent_el, 'alternateIdentifiers', is_list=True)
        for identifier in sorted(self.basket[DCTERMS.identifier]):
            identifier_type, identifier_value = self._identifier_type_and_value(identifier)
            if identifier_value and (identifier_type != 'DOI'):
                self.visit(alt_ids_el, 'alternateIdentifier', text=identifier_value, attrib={
                    'alternateIdentifierType': identifier_type,
                })

    def _visit_titles(self, parent_el, focus_iri):
        titles_el = self.visit(parent_el, 'titles', is_list=True)
        for title in self.basket[focus_iri:DCTERMS.title]:
            self.visit(titles_el, 'title', text=title)
        if (not len(titles_el)) and (OSF.File in self.basket[focus_iri:RDF.type]):
            self.visit(titles_el, 'title', text=next(self.basket[focus_iri:OSF.fileName]))

    def _visit_descriptions(self, parent_el, focus_iri):
        descriptions_el = self.visit(parent_el, 'descriptions', is_list=True)
        for description in self.basket[focus_iri:DCTERMS.description]:
            self.visit(descriptions_el, 'description', text=description, attrib={
                'descriptionType': 'Abstract',  # TODO: other description types?
            })

    def _visit_publisher(self, parent_el, focus_iri):
        publisher_name = next(self.basket[focus_iri:DCTERMS.publisher / FOAF.name], 'OSF')
        self.visit(parent_el, 'publisher', text=publisher_name)

    def _agent_name_type(self, agent_iri):
        agent_types = set(self.basket[agent_iri:RDF.type])
        if FOAF.Person in agent_types:
            return 'Personal'
        if FOAF.Organization in agent_types:
            return 'Organizational'
        raise ValueError(f'unknown agent type for {agent_iri}')

    def _visit_contributors(self, parent_el, focus_iri):
        contributors_el = self.visit(parent_el, 'contributors', is_list=True)
        for osfmap_iri, datacite_contributor_type in CONTRIBUTOR_TYPE_MAP.items():
            for contributor_iri in self.basket[focus_iri:osfmap_iri]:
                contributor_el = self.visit(contributors_el, 'contributor', attrib={
                    'contributorType': datacite_contributor_type,
                })
                for name in self.basket[contributor_iri:FOAF.name]:
                    self.visit(contributor_el, 'contributorName', text=name, attrib={
                        'nameType': self._get_name_type(contributor_iri),
                    })
                self._visit_name_identifiers(contributor_el, contributor_iri)
                self._visit_affiliations(contributor_el, contributor_iri)

    def _visit_rights(self, parent_el):
        rights_list_el = self.visit(parent_el, 'rightsList', is_list=True)
        for rights_iri in self.basket[DCTERMS.rights]:
            name = next(self.basket[rights_iri:FOAF.name], '')
            try:
                attrib = {
                    'rightsURI': next(self.basket[rights_iri:DCTERMS.identifier]),
                }
            except StopIteration:
                attrib = {}
            self.visit(rights_list_el, 'rights', text=name, attrib=attrib)

    def _visit_affiliations(self, parent_el, focus_iri):
        for institution_iri in self.basket[focus_iri:OSF.affiliation]:
            try:
                name = next(self.basket[institution_iri:FOAF.name])
            except StopIteration:
                raise MetadataSerializationError(f'need foaf:name for affiliated "{focus_iri}"')
            affiliation_attrib = {}
            try:
                identifier = self._get_one_identifier(institution_iri)
            except ValueError:
                pass  # don't need affiliationIdentifier
            else:
                identifier_type, identifier_value = self._identifier_type_and_value(identifier)
                if identifier_value:
                    affiliation_attrib['affiliationIdentifier'] = identifier_value
                    affiliation_attrib['affiliationIdentifierScheme'] = identifier_type
            self.visit(parent_el, 'affiliation', text=name, attrib=affiliation_attrib, is_list=True)

    def _visit_dates(self, parent_el):
        dates_el = self.visit(parent_el, 'dates', is_list=True)
        for date_predicate, datacite_datetype in DATE_TYPE_MAP.items():
            for date_str in self.basket[date_predicate]:
                self.visit(dates_el, 'date', text=date_str, attrib={
                    'dateType': datacite_datetype,
                })

    def _visit_funding_references(self, parent_el):
        fundrefs_el = self.visit(parent_el, 'fundingReferences', is_list=True)
        _visited_funders = set()
        for _funding_award in sorted(self.basket[OSF.hasFunding]):
            # datacite allows at most one funder per funding reference
            _funder = next(self.basket[_funding_award:DCTERMS.contributor])
            self._funding_reference(fundrefs_el, _funder, _funding_award)
            _visited_funders.add(_funder)
        for _funder in self.basket[OSF.funder]:
            if _funder not in _visited_funders:
                self._funding_reference(fundrefs_el, _funder)

    def _funding_reference(self, fundrefs_el, funder, funding_award=None):
        _fundref_el = self.visit(fundrefs_el, 'fundingReference')
        self.visit(_fundref_el, 'funderName', text=next(self.basket[funder:FOAF.name], ''))
        _funder_identifier = next(self.basket[funder:DCTERMS.identifier], '')
        self.visit(
            _fundref_el,
            'funderIdentifier',
            text=_funder_identifier,
            attrib={
                'funderIdentifierType': self._funder_identifier_type(_funder_identifier),
            },
        )
        if funding_award is not None:
            self.visit(
                _fundref_el,
                'awardNumber',
                text=next(self.basket[funding_award:OSF.awardNumber], ''),
                attrib={
                    'awardURI': (
                        str(funding_award)
                        if isinstance(funding_award, rdflib.URIRef)
                        else ''
                    )
                },
            )
            self.visit(_fundref_el, 'awardTitle', text=next(self.basket[funding_award:DCTERMS.title], ''))

    def _visit_publication_year(self, parent_el, focus_iri):
        year_copyrighted = next(self.basket[focus_iri:DCTERMS.dateCopyrighted], None)
        if year_copyrighted and re.fullmatch(r'\d{4}', year_copyrighted):
            self.visit(parent_el, 'publicationYear', text=year_copyrighted)
        else:
            for date_predicate in PUBLICATION_YEAR_FALLBACK_ORDER:
                date_str = next(self.basket[focus_iri:date_predicate], None)
                if date_str:
                    extracted_year = str(datetime.datetime.strptime(date_str, '%Y-%m-%d').year)
                    self.visit(parent_el, 'publicationYear', text=extracted_year)
                    break  # only one allowed

    def _visit_language(self, parent_el):
        try:
            language = next(self.basket[DCTERMS.language])
        except StopIteration:
            pass
        else:
            self.visit(parent_el, 'language', text=language)

    def _visit_format(self, parent_el):
        try:
            format_val = next(self.basket[DCTERMS['format']])
        except StopIteration:
            pass
        else:
            self.visit(parent_el, 'format', text=format_val)

    def _get_one_identifier(self, resource_id) -> str:
        try:  # prefer DOI if there is one
            chosen_identifier = next(
                identifier
                for identifier in self.basket[resource_id:DCTERMS.identifier]
                if identifier.startswith(DOI)
            )
        except StopIteration:
            try:  # ...but any IRI will do
                chosen_identifier = next(self.basket[resource_id:DCTERMS.identifier])
            except StopIteration:
                if isinstance(resource_id, rdflib.URIRef):
                    chosen_identifier = str(resource_id)
                else:
                    raise ValueError(f'no identifier found for {resource_id}')
        return chosen_identifier

    def _visit_related_identifier_and_item(self, identifier_parent_el, item_parent_el, related_iri, datacite_relation_type):
        try:
            identifier = self._get_one_identifier(related_iri)
        except ValueError:
            identifier = None  # can add relatedItem without identifier
        related_item_el = self.visit(item_parent_el, 'relatedItem', attrib={
            'relationType': datacite_relation_type,
            'relatedItemType': self._get_resource_type_general(related_iri),
        })
        if identifier is not None:
            identifier_type, identifier_value = self._identifier_type_and_value(identifier)
            if identifier_value:
                self.visit(related_item_el, 'relatedItemIdentifier', text=identifier_value, attrib={
                    'relatedItemIdentifierType': identifier_type,
                })
                self.visit(identifier_parent_el, 'relatedIdentifier', text=identifier_value, attrib={
                    'relatedIdentifierType': identifier_type,
                    'relationType': datacite_relation_type,
                })
        self._visit_titles(related_item_el, related_iri)
        self._visit_publication_year(related_item_el, related_iri)
        self._visit_publisher(related_item_el, related_iri)

    def _visit_related_and_verified_links(self, parent_el):
        relation_pairs = set()
        for relation_iri, datacite_relation in RELATED_IDENTIFIER_TYPE_MAP.items():
            for related_iri in self.basket[relation_iri]:
                relation_pairs.add((datacite_relation, related_iri))

        related_identifiers_el = self.visit(parent_el, 'relatedIdentifiers', is_list=True)
        related_items_el = self.visit(parent_el, 'relatedItems', is_list=True)

        # First add regular related identifiers
        for datacite_relation, related_iri in sorted(relation_pairs):
            self._visit_related_identifier_and_item(
                related_identifiers_el,
                related_items_el,
                related_iri,
                datacite_relation,
            )

        # Then add verified links to same relatedIdentifiers element
        osf_item = self.basket.focus.dbmodel
        from osf.models import AbstractNode

        if isinstance(osf_item, AbstractNode):
            gv_verified_link_list = list(get_verified_links(node_guid=osf_item._id))
            if gv_verified_link_list:
                non_url_verified_links = []
                for item in gv_verified_link_list:
                    verified_link, resource_type = item.attributes.get('target_url', None), item.attributes.get('resource_type', None)
                    if verified_link and resource_type:
                        if smells_like_iri(verified_link):
                            self.visit(related_identifiers_el, 'relatedIdentifier', text=verified_link, attrib={
                                'relatedIdentifierType': 'URL',
                                'relationType': 'IsReferencedBy',
                                'resourceTypeGeneral': resource_type.title()
                            })
                        else:
                            non_url_verified_links.append(verified_link)
                if non_url_verified_links:
                    sentry.log_message(f'Skipped - {','.join(non_url_verified_links)} for node {osf_item._id}')

    def _visit_name_identifiers(self, parent_el, agent_iri):
        for identifier in sorted(self.basket[agent_iri:DCTERMS.identifier]):
            identifier_type, identifier_value = self._identifier_type_and_value(identifier)
            if identifier_value:
                self.visit(parent_el, 'nameIdentifier', text=identifier_value, attrib={
                    'nameIdentifierScheme': identifier_type,
                })

    def _visit_subjects(self, parent_el):
        subjects_el = self.visit(parent_el, 'subjects', is_list=True)
        for subject in sorted(self.basket[DCTERMS.subject]):
            _subject_label = next(self.basket[subject:SKOS.prefLabel], None)
            if _subject_label:
                _attrib = {}
                _subject_scheme_title = next(self.basket[subject:SKOS.inScheme / DCTERMS.title], None)
                if _subject_scheme_title:
                    _attrib['subjectScheme'] = _subject_scheme_title
                self.visit(subjects_el, 'subject', text=_subject_label, attrib=_attrib)
        for keyword in sorted(self.basket[OSF.keyword]):
            self.visit(subjects_el, 'subject', text=keyword)

    def _visit_resource_type(self, parent_el):
        resource_type_text = ''
        focustype = self.basket.focus.rdftype
        if focustype.startswith(OSF):
            if focustype == OSF.Registration:
                # for back-compat until datacite 4.5 adds resourceTypeGeneral='StudyRegistration'
                resource_type_text = 'Pre-registration'
            else:
                resource_type_text = without_namespace(focustype, OSF)
        self.visit(parent_el, 'resourceType', text=resource_type_text, attrib={
            'resourceTypeGeneral': self._get_resource_type_general(self.basket.focus.iri),
        })

    def _get_resource_type_general(self, focus_iri):
        # return just the first recognized type, preferably from dcterms:type
        type_terms = itertools.chain(
            self.basket[focus_iri:DCTERMS.type],
            self.basket[focus_iri:RDF.type],
        )
        for type_term in type_terms:
            if isinstance(type_term, rdflib.URIRef) and type_term.startswith(DATACITE):
                return without_namespace(type_term, DATACITE)
        return 'Text'
