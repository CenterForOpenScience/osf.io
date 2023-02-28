from datetime import datetime
import json

from datacite import schema43 as datacite_schema43
import rdflib

from framework import sentry
from website import settings
from osf.metadata import gather
from osf.metadata.rdfutils import (
    DCT,
    DOI,
    FOAF,
    ORCID,
    OSF,
    OWL,
    ROR,
    primitivify_rdf,
)
from osf.metadata.serializers import _base


class DataciteJsonMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'application/json'

    def filename(self, osfguid: str):
        return f'{osfguid}-datacite.json'

    def serialize(self, basket: gather.Basket):
        metadata = {
            'schemaVersion': 'http://datacite.org/schema/kernel-4',
            'publisher': 'Open Science Framework',
            'identifiers': [{
                'identifier': self._focus_doi_value(basket),
                'identifierType': 'DOI',
            }, {
                'identifier': basket.focus.iri,
                'identifierType': 'URL',
            }],
            'rightsList': _format_rights(basket),
            'titles': _format_titles(basket),
            'descriptions': [
                {
                    'descriptionType': 'Abstract',
                    'description': description,
                }
                for description in basket[DCT.description]
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
        language = next(basket[DCT.language], None)  # only one allowed?
        if language:
            metadata['language'] = language

        metadata = primitivify_rdf(metadata)
        try:
            datacite_schema43.validator.validate(metadata)
        except Exception:
            sentry.log_exception()
            raise
        if self.serializer_config.get('as_dict'):
            return metadata
        return json.dumps(metadata, indent=2, sort_keys=True)

    def _focus_doi_value(self, basket):
        chosen_doi = self.serializer_config.get('doi_value')
        if chosen_doi is not None:
            return chosen_doi
        focus_iri = basket.focus.iri
        if focus_iri.startswith(DOI):
            return focus_iri[len(DOI):]
        for synonym_iri in basket[OWL.sameAs]:
            if synonym_iri.startswith(DOI):
                return synonym_iri[len(DOI):]
        return ''


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


def _format_titles(basket):
    titles = list(basket[DCT.title])
    if not titles and basket.focus.rdftype == OSF.File:
        titles.append(next(basket[OSF.file_name], ''))
    return [
        {'title': title}
        for title in titles
    ]


def _format_contributors(basket):
    contributors_json = []
    for contributor_iri in basket[DCT.contributor]:
        contributors_json.append({
            'contributorType': 'ProjectMember',
            'name': next(basket[contributor_iri:FOAF.name], ''),
            'nameIdentifiers': _format_name_identifiers(basket, contributor_iri),
            'nameType': 'Personal',
            'affiliation': _format_affiliations(basket, contributor_iri),
        })
    contributors_json.append({
        'nameType': 'Organizational',
        'contributorType': 'HostingInstitution',
        'contributorName': 'Open Science Framework',
        'name': 'Open Science Framework',
        'nameIdentifiers': [
            {
                'name': 'Open Science Framework',
                'nameIdentifier': ROR[settings.OSF_ROR_ID],
                'nameIdentifierScheme': 'ROR',
            },
            {
                'name': 'Open Science Framework',
                'nameIdentifier': f'https://grid.ac/institutes/{settings.OSF_GRID_ID}/',
                'nameIdentifierScheme': 'GRID',
            }
        ],
    })
    return contributors_json


def _format_rights(basket):
    rights_list = []
    for rights_value in basket[DCT.rights]:
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
    for institution_iri in basket[focus_iri:OSF.affiliated_institution]:
        name = next(basket[institution_iri:FOAF.name], None)
        identifiers = basket[institution_iri:DCT.identifier]
        if name and not identifiers:
            affiliations.append({'name': name})
        for identifier in identifiers:
            if identifier.startswith(ROR):
                affiliations.append({
                    'name': name,
                    'affiliationIdentifier': identifier,
                    'affiliationIdentifierScheme': 'ROR',
                    'SchemeURI': ROR,
                })
            else:
                affiliations.append({
                    'name': name,
                    'affiliationIdentifier': identifier,
                    'affiliationIdentifierScheme': 'URL',
                })
    return affiliations


def _format_name(basket, agent_iri, name_type='Personal'):
    return {
        'name': next(basket[agent_iri:FOAF.name], ''),
        'nameIdentifiers': _format_name_identifiers(basket, agent_iri),
        'nameType': name_type,
        'affiliation': _format_affiliations(basket, agent_iri),
    }


def _format_creators(basket):
    creator_iris = set(basket[DCT.creator])
    if (not creator_iris) and (basket.focus.rdftype == OSF.File):
        creator_iris.update(basket[DCT.hasVersion / DCT.creator])
    if not creator_iris:
        creator_iris.update(basket[DCT.isPartOf / DCT.creator])
    if not creator_iris:
        creator_iris.update(basket[DCT.contributor])
    if not creator_iris:
        creator_iris.update(basket[DCT.isPartOf / DCT.contributor])
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
            'dateType': datacite_datetype,
        }


def _format_dates(basket):
    return [
        *_format_date(basket, DCT.created, 'Created'),
        *_format_date(basket, DCT.modified, 'Updated'),
        *_format_date(basket, DCT.issued, 'Issued'),
    ]


def _format_funding_references(basket):
    funding_references = []
    for funding_ref in basket[OSF.funder]:
        funding_references.append({
            'funderName': next(basket[funding_ref:FOAF.name], ''),
            'funderIdentifier': next(basket[funding_ref:DCT.identifier], ''),
            'funderIdentifierType': next(basket[funding_ref:OSF.funder_identifier_type], ''),
            'awardNumber': next(basket[funding_ref:OSF.award_number], ''),
            'awardURI': next(basket[funding_ref:OSF.award_uri], ''),
            'awardTitle': next(basket[funding_ref:OSF.award_title], ''),
        })
    return funding_references


def _format_publication_year(basket):
    year_copyrighted = next(basket[DCT.dateCopyrighted], None)
    if year_copyrighted:
        return year_copyrighted
    for date_predicate in (DCT.available, DCT.dateAccepted, DCT.created, DCT.modified):
        date_str = next(basket[date_predicate], None)
        if date_str:
            return str(datetime.strptime(date_str, '%Y-%m-%d').year)


def _format_related_identifier(related_iri, datacite_relation_type):
    if related_iri.startswith(DOI):
        identifier_type = 'DOI'
        identifier = related_iri[len(DOI):]
    else:
        identifier_type = 'URL'
        identifier = related_iri
    return {
        'relatedIdentifier': identifier,
        'relatedIdentifierType': identifier_type,
        'relationType': datacite_relation_type,
    }


def _format_related_identifiers(basket):
    related_identifiers = []
    artifact_predicates = (
        OSF.data_resource,
        OSF.analytic_code_resource,
        OSF.materials_resource,
        OSF.papers_resource,
        OSF.supplements_resource,
    )
    supplemented_by = set()
    for artifact_predicate in artifact_predicates:
        supplemented_by.update(basket[artifact_predicate / DCT.identifier])
    for related_iri in supplemented_by:
        related_identifiers.append(
            _format_related_identifier(related_iri, 'IsSupplementedBy'),
        )
    for related_iri in basket[OSF.is_supplement_to_article]:
        related_identifiers.append(
            _format_related_identifier(related_iri, 'IsSupplementTo'),
        )
    for related_iri in basket[DCT.isPartOf]:
        related_identifiers.append(
            _format_related_identifier(related_iri, 'IsPartOf'),
        )
    # TODO: HasPart as well -- but large numbers of files could be problems

    return related_identifiers


def _format_name_identifiers(basket, agent_iri):
    name_identifiers = []
    for identifier in basket[agent_iri:DCT.identifier]:
        if identifier.startswith(ORCID):
            name_identifiers.append({
                'nameIdentifier': identifier,
                'nameIdentifierScheme': 'ORCID',
                'schemeURI': ORCID,
            })
        else:
            name_identifiers.append({
                'nameIdentifier': identifier,
                'nameIdentifierScheme': 'URL',
            })
    return name_identifiers


def _format_subjects(basket):
    datacite_subjects = []
    for subject in basket[DCT.subject]:
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
        types['resourceType'] = focustype[len(OSF):]
    if types['resourceType'] == 'Registration':
        types['resourceType'] = 'Pre-registration'  # for back-compat
    for general_type in basket[DCT.type]:
        if isinstance(general_type, rdflib.Literal):
            general_type = str(general_type)
            if general_type in RESOURCE_TYPES_GENERAL:
                types['resourceTypeGeneral'] = general_type
    return types
