from datetime import datetime
import json
import re

from datacite import schema43 as datacite_schema43
import rdflib

from framework import sentry
from website import settings
from osf.metadata import gather
from osf.metadata.rdfutils import (
    DATACITE,
    DCTERMS,
    DOI,
    FOAF,
    ORCID,
    OSF,
    ROR,
    primitivify_rdf,
    without_namespace,
)
from osf.metadata.serializers import _base


RELATED_IDENTIFIER_TYPE_MAP = {
    DCTERMS.hasPart: DATACITE.HasPart,
    DCTERMS.hasVersion: DATACITE.HasVersion,
    DCTERMS.isPartOf: DATACITE.IsPartOf,
    DCTERMS.isVersionOf: DATACITE.IsVersionOf,
    DCTERMS.references: DATACITE.References,
    DCTERMS.relation: DATACITE.References,
    OSF.archivedAt: DATACITE.IsIdenticalTo,
    OSF.hasRoot: DATACITE.IsPartOf,
    OSF.isContainedBy: DATACITE.IsPartOf,
    OSF.supplements: DATACITE.IsSupplementTo,
    OSF.isSupplementedBy: DATACITE.IsSupplementedBy,
}
BEPRESS_SUBJECT_SCHEME = 'bepress Digital Commons Three-Tiered Taxonomy'
RESOURCE_TYPES_GENERAL = {
    'Audiovisual',
    'Collection',
    'DataPaper',
    'Dataset',
    'Event',
    'Image',
    'InteractiveResource',
    'Model',
    'PhysicalObject',
    'Service',
    'Software',
    'Sound',
    'Text',
    'Workflow',
    'Other',
}


class DataciteJsonMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'application/json'

    def filename(self, osfguid: str):
        return f'{osfguid}-datacite.json'

    def serialize(self, basket: gather.Basket):
        return json.dumps(self.primitivize(basket), indent=2, sort_keys=True)

    def primitivize(self, basket: gather.Basket):
        metadata = {
            'schemaVersion': 'http://datacite.org/schema/kernel-4',
            'publisher': next(basket[DCTERMS.publisher / FOAF.name], 'OSF'),
            'identifiers': _format_focus_identifiers(
                basket,
                chosen_doi=self.serializer_config.get('doi_value'),
            ),
            'rightsList': _format_rights(basket),
            'titles': _format_titles(basket),
            'descriptions': [
                {
                    'descriptionType': 'Abstract',
                    'description': description,
                }
                for description in basket[DCTERMS.description]
            ],
            'contributors': _format_contributors(basket),
            'creators': _format_creators(basket),
            'dates': _format_dates(basket),
            'fundingReferences': _format_funding_references(basket),
            'publicationYear': _format_publication_year(basket),
            'relatedIdentifiers': _format_related_identifiers(basket),
            'subjects': _format_subjects(basket),
            'types': _format_types(basket),
        }
        language = next(basket[DCTERMS.language], None)  # only one allowed?
        if language:
            metadata['language'] = language

        metadata = primitivify_rdf(metadata)
        try:
            datacite_schema43.validator.validate(metadata)
        except Exception:
            sentry.log_exception()
            raise
        return metadata


def _iter_identifier_value_and_type(basket, focus_iri):
    for iri in basket[focus_iri:DCTERMS.identifier]:
        if iri.startswith(DOI):
            yield (without_namespace(iri, DOI), DATACITE.DOI)
        elif iri.startswith(ROR):
            yield (without_namespace(iri, ROR), DATACITE.ROR)
        elif iri.startswith(ORCID):
            yield (without_namespace(iri, ORCID), DATACITE.ORCID)
        else:
            yield (iri, DATACITE.URL)


def _format_focus_identifiers(basket, *, chosen_doi=None):
    focus_identifiers = []
    if chosen_doi is not None:
        focus_identifiers.append({'identifier': chosen_doi, 'identifierType': 'DOI'})
    focus_identifiers.extend((
        {
            'identifier': id_value,
            'identifierType': without_namespace(id_type, DATACITE),
        }
        for id_value, id_type in _iter_identifier_value_and_type(basket, basket.focus.iri)
        if not (
            chosen_doi == id_value
            and id_type == DATACITE.DOI
        )
    ))

    def doi_first__sortkey(id_dict):
        return (id_dict['identifierType'] != 'DOI')
    return sorted(focus_identifiers, key=doi_first__sortkey)


def _format_titles(basket):
    titles = list(basket[DCTERMS.title])
    if not titles and basket.focus.rdftype == OSF.File:
        titles.append(next(basket[OSF.fileName], ''))
    return [
        {'title': title}
        for title in titles
    ]


def _agent_name_type(basket, agent_iri):
    agent_types = set(basket[agent_iri:DCTERMS.type])
    if FOAF.Person in agent_types:
        return 'Personal'
    if FOAF.Organization in agent_types:
        return 'Organizational'
    raise ValueError(f'unknown agent type for {agent_iri}')


def _format_contributors(basket):
    contributors_json = []
    for contributor_iri in basket[DCTERMS.contributor]:
        contributors_json.append({
            **_format_name(basket, contributor_iri),
            'contributorType': 'ProjectMember',
        })
    contributors_json.append({
        'nameType': 'Organizational',
        'contributorType': 'HostingInstitution',
        'contributorName': 'Center for Open Science',
        'name': 'Center for Open Science',
        'nameIdentifiers': [
            {
                'name': 'Center for Open Science',
                'nameIdentifier': ROR[settings.OSF_ROR_ID],
                'nameIdentifierScheme': 'ROR',
            },
            {
                'name': 'Center for Open Science',
                'nameIdentifier': f'https://grid.ac/institutes/{settings.OSF_GRID_ID}/',
                'nameIdentifierScheme': 'GRID',
            }
        ],
    })
    return contributors_json


def _format_rights(basket):
    rights_list = []
    for rights_value in basket[DCTERMS.rights]:
        if isinstance(rights_value, rdflib.URIRef):
            rights_list.append({
                'rights': next(basket[rights_value:FOAF.name], ''),
                'rightsUri': rights_value,
            })
        elif isinstance(rights_value, rdflib.Literal):
            rights_list.append({'rights': rights_value})
    return rights_list


def _format_affiliations(basket, focus_iri):
    affiliations = []
    for institution_iri in basket[focus_iri:OSF.affiliatedInstitution]:
        name = next(basket[institution_iri:FOAF.name], None)
        affiliations.append({
            'name': name,
            'nameType': 'Organizational',
            'affiliationIdentifiers': [
                {
                    'affiliationIdentifier': id_value,
                    'affiliationIdentifierScheme': without_namespace(id_type, DATACITE),
                }
                for id_value, id_type in _iter_identifier_value_and_type(basket, institution_iri)
            ],
        })
    return affiliations


def _format_name(basket, agent_iri):
    return {
        'name': next(basket[agent_iri:FOAF.name], ''),
        'nameIdentifiers': _format_name_identifiers(basket, agent_iri),
        'nameType': _agent_name_type(basket, agent_iri),
        'affiliation': _format_affiliations(basket, agent_iri),
    }


def _format_creators(basket):
    creator_iris = set(basket[DCTERMS.creator])
    if (not creator_iris) and (basket.focus.rdftype == OSF.File):
        creator_iris.update(basket[DCTERMS.hasVersion / DCTERMS.creator])
    if not creator_iris:
        creator_iris.update(basket[OSF.isContainedBy / DCTERMS.creator])
    if not creator_iris:
        creator_iris.update(basket[DCTERMS.isPartOf / DCTERMS.creator])
    if not creator_iris:
        creator_iris.update(basket[DCTERMS.contributor])
    if not creator_iris:
        creator_iris.update(basket[OSF.isContainedBy / DCTERMS.contributor])
    if not creator_iris:
        creator_iris.update(basket[DCTERMS.isPartOf / DCTERMS.contributor])
    if not creator_iris:
        raise ValueError(f'gathered no creators or contributors around {basket.focus.iri}')
    return [
        _format_name(basket, creator_iri)
        for creator_iri in creator_iris
    ]


def _format_date(basket, date_iri, datacite_datetype):
    for date_str in basket[date_iri]:
        yield {
            'date': date_str,
            'dateType': without_namespace(datacite_datetype, DATACITE),
        }


def _format_dates(basket):
    return [
        *_format_date(basket, DCTERMS.created, DATACITE.Created),
        *_format_date(basket, DCTERMS.modified, DATACITE.Updated),
        *_format_date(basket, DCTERMS.dateSubmitted, DATACITE.Submitted),
        *_format_date(basket, DCTERMS.dateAccepted, DATACITE.Valid),
        *_format_date(basket, DCTERMS.available, DATACITE.Available),
        *_format_date(basket, DCTERMS.date, DATACITE.Other),
        *_format_date(basket, OSF.withdrawn, DATACITE.Withdrawn),
    ]


def _format_funding_references(basket):
    funding_references = []
    for funding_ref in basket[OSF.funder]:
        funding_references.append({
            'funderName': next(basket[funding_ref:FOAF.name], ''),
            'funderIdentifier': next(basket[funding_ref:DCTERMS.identifier], ''),
            'funderIdentifierType': next(basket[funding_ref:OSF.funderIdentifierType], ''),
            'awardNumber': next(basket[funding_ref:OSF.awardNumber], ''),
            'awardURI': next(basket[funding_ref:OSF.awardUri], ''),
            'awardTitle': next(basket[funding_ref:OSF.awardTitle], ''),
        })
    return funding_references


def _format_publication_year(basket):
    year_copyrighted = next(basket[DCTERMS.dateCopyrighted], None)
    if year_copyrighted and re.fullmatch(r'\d{4}', year_copyrighted):
        return year_copyrighted
    for date_predicate in (DCTERMS.available, DCTERMS.dateAccepted, DCTERMS.created, DCTERMS.modified):
        date_str = next(basket[date_predicate], None)
        if date_str:
            return str(datetime.strptime(date_str, '%Y-%m-%d').year)


def _format_related_identifier(basket, related_iri, datacite_relation_type):
    try:  # prefer DOI if there is one
        identifier = next(
            without_namespace(iri, DOI)
            for iri in basket[related_iri:DCTERMS.identifier]
            if iri.startswith(DOI)
        )
        identifier_type = 'DOI'
    except StopIteration:
        try:
            identifier = (
                str(related_iri)
                if isinstance(related_iri, rdflib.URIRef)
                else next(basket[related_iri:DCTERMS.identifier])
            )
            identifier_type = 'URL'
        except StopIteration:
            raise ValueError(f'related_iri ({related_iri}) must have dcterms:identifier or be an iri')
    return {
        'relatedIdentifier': identifier,
        'relatedIdentifierType': identifier_type,
        'relationType': without_namespace(datacite_relation_type, DATACITE),
    }


def _format_related_identifiers(basket):
    related_identifiers = []
    artifact_predicates = (
        OSF.hasDataResource,
        OSF.hasAnalyticCodeResource,
        OSF.hasMaterialsResource,
        OSF.hasPapersResource,
        OSF.hasSupplementalResource,
    )
    referenced_artifact_iris = set()
    for artifact_predicate in artifact_predicates:
        referenced_artifact_iris.update(basket[artifact_predicate])
    for referenced_iri in referenced_artifact_iris:
        related_identifiers.append(
            _format_related_identifier(basket, referenced_iri, DATACITE.References),
        )
    for relation_iri, datacite_relation in RELATED_IDENTIFIER_TYPE_MAP.items():
        for related_iri in basket[relation_iri]:
            related_identifiers.append(
                _format_related_identifier(basket, related_iri, datacite_relation),
            )
    return list(_deduplicated_dicts(related_identifiers))


def _format_name_identifiers(basket, agent_iri):
    return [
        {
            'nameIdentifier': id_value,
            'nameIdentifierScheme': without_namespace(id_type, DATACITE),
        }
        for id_value, id_type in _iter_identifier_value_and_type(basket, agent_iri)
    ]


def _format_subjects(basket):
    datacite_subjects = []
    for subject in basket[DCTERMS.subject]:
        datacite_subjects.append({
            'subject': subject,
            'subjectScheme': BEPRESS_SUBJECT_SCHEME,
        })
    for keyword in basket[OSF.keyword]:
        datacite_subjects.append({
            'subject': keyword,
            'subjectScheme': OSF.keyword,
        })
    return datacite_subjects


def _format_types(basket):
    focustype = basket.focus.rdftype
    types = {
        'resourceType': focustype,
        'resourceTypeGeneral': 'Text',
    }
    if focustype.startswith(OSF):
        if focustype == OSF.Registration:
            types['resourceType'] = 'Pre-registration'  # for back-compat
        else:
            types['resourceType'] = without_namespace(focustype, OSF)
    for general_type in basket[DCTERMS.type]:
        if isinstance(general_type, rdflib.Literal):
            general_type = str(general_type)
            if general_type in RESOURCE_TYPES_GENERAL:
                types['resourceTypeGeneral'] = general_type
    return types


def _deduplicated_dicts(list_of_dict):
    seen = set()
    for each_dict in list_of_dict:
        seen_key = frozenset(each_dict.items())
        if seen_key not in seen:
            seen.add(seen_key)
            yield each_dict
