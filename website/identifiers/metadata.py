# -*- coding: utf-8 -*-
import time

import unicodedata
import lxml.etree
import lxml.builder

from website import settings

NAMESPACE = 'http://datacite.org/schema/kernel-4'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
SCHEMA_LOCATION = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd'
E = lxml.builder.ElementMaker(nsmap={
    None: NAMESPACE,
    'xsi': XSI},
)
DOI_URL_PREFIX = 'https://dx.doi.org/'

CROSSREF_NAMESPACE = 'http://www.crossref.org/schema/4.4.1'
CROSSREF_SCHEMA_LOCATION = 'http://www.crossref.org/schema/4.4.1 http://www.crossref.org/schemas/crossref4.4.1.xsd'
CROSSREF_ACCESS_INDICATORS = 'http://www.crossref.org/AccessIndicators.xsd'
CROSSREF_RELATIONS = 'http://www.crossref.org/relations.xsd'
CROSSREF_SCHEMA_VERSION = '4.4.1'
JATS_NAMESPACE = 'http://www.ncbi.nlm.nih.gov/JATS1'

CROSSREF_DEPOSITOR_NAME = 'Open Science Framework'
CROSSREF_DEPOSITOR_EMAIL = 'crossref@osf.io'

CREATOR = E.creator
CREATOR_NAME = E.creatorName
SUBJECT_SCHEME = 'bepress Digital Commons Three-Tiered Taxonomy'

# From https://stackoverflow.com/a/19016117
# lxml does not accept strings with control characters
def remove_control_characters(s):
    return ''.join(ch for ch in s if unicodedata.category(ch)[0] != 'C')

# This function is not OSF-specific
def datacite_metadata(doi, title, creators, publisher, publication_year, pretty_print=False):
    """Return the formatted datacite metadata XML as a string.

    :param str doi
    :param str title
    :param list creators: List of creator names, formatted like 'Shakespeare, William'
    :param str publisher: Publisher name.
    :param int publication_year
    :param bool pretty_print
    """
    creators = [CREATOR(CREATOR_NAME(each)) for each in creators]
    root = E.resource(
        E.resourceType('Project', resourceTypeGeneral='Text'),
        E.identifier(doi, identifierType='DOI'),
        E.creators(*creators),
        E.titles(E.title(remove_control_characters(title))),
        E.publisher(publisher),
        E.publicationYear(str(publication_year)),
    )
    # set xsi:schemaLocation
    root.attrib['{%s}schemaLocation' % XSI] = SCHEMA_LOCATION
    return lxml.etree.tostring(root, pretty_print=pretty_print)


def format_contributor(contributor):
    return remove_control_characters(u'{}, {}'.format(contributor.family_name, contributor.given_name))


# This function is OSF specific.
def datacite_metadata_for_node(node, doi, pretty_print=False):
    """Return the datacite metadata XML document for a given node as a string.

    :param Node node
    :param str doi
    """
    creators = [format_contributor(each) for each in node.visible_contributors]
    return datacite_metadata(
        doi=doi,
        title=node.title,
        creators=creators,
        publisher='Open Science Framework',
        publication_year=getattr(node.registered_date or node.created, 'year'),
        pretty_print=pretty_print
    )


def format_creators(preprint):
    creators = []
    for contributor in preprint.node.visible_contributors:
        creator = CREATOR(E.creatorName(format_contributor(contributor)))
        creator.append(E.givenName(remove_control_characters(contributor.given_name)))
        creator.append(E.familyName(remove_control_characters(contributor.family_name)))
        creator.append(E.nameIdentifier(contributor.absolute_url, nameIdentifierScheme='OSF', schemeURI=settings.DOMAIN))

        # contributor.external_identity = {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        if contributor.external_identity.get('ORCID'):
            verified = contributor.external_identity['ORCID'].values()[0] == 'VERIFIED'
            if verified:
                creator.append(E.nameIdentifier(contributor.external_identity['ORCID'].keys()[0], nameIdentifierScheme='ORCID', schemeURI='http://orcid.org/'))

        creators.append(creator)

    return creators


def format_subjects(preprint):
    return [E.subject(subject, subjectScheme=SUBJECT_SCHEME) for subject in preprint.subjects.values_list('text', flat=True)]


def format_contributors_crossref(element, preprint):
    contributors = []
    for index, contributor in enumerate(preprint.node.visible_contributors):
        if index == 0:
            sequence = 'first'
        else:
            sequence = 'additional'

        person = element.person_name(sequence=sequence, contributor_role='author')
        contributor_given_plus_middle = remove_control_characters(
            ' '.join([contributor.given_name, contributor.middle_names]).strip()
        )
        person.append(element.given_name(contributor_given_plus_middle))
        person.append(element.surname(remove_control_characters(contributor.family_name)))
        if contributor.suffix:
            person.append(element.suffix(remove_control_characters(contributor.suffix)))

        contributors.append(person)

    return contributors


def format_date_crossref(element, date):
    elements = [
        element.month(date.strftime('%m')),
        element.day(date.strftime('%d')),
        element.year(date.strftime('%Y'))
    ]
    return elements


def crossref_metadata_for_preprint(preprint, doi, pretty_print=False):
    """Return the crossref metadata XML document for a given preprint as a string for DOI minting purposes

    :param preprint -- the preprint
    """
    element = lxml.builder.ElementMaker(nsmap={
        None: CROSSREF_NAMESPACE,
        'xsi': XSI},
    )

    head = element.head(
        element.doi_batch_id(preprint._id),  # TODO -- CrossRef has said they don't care about this field, is this OK?
        element.timestamp('{}'.format(int(time.time()))),
        element.depositor(
            element.depositor_name(CROSSREF_DEPOSITOR_NAME),
            element.email_address(CROSSREF_DEPOSITOR_EMAIL)
        ),
        element.registrant(preprint.provider.name)  # TODO - confirm provider name is desired
    )

    posted_content = element.posted_content(
        element.group_title(preprint.provider._id),
        element.contributors(*format_contributors_crossref(element, preprint)),
        element.titles(element.title(preprint.node.title)),
        element.posted_date(*format_date_crossref(element, preprint.date_published)),
        element.item_number('osf.io/{}'.format(preprint._id)),
        type='preprint'
    )

    if preprint.node.description:
        posted_content.append(element.abstract(element.p(preprint.node.description), xmlns=JATS_NAMESPACE))

    if preprint.license and preprint.license.node_license.url:
        posted_content.append(
            element.program(
                element.license_ref(preprint.license.node_license.url, start_date=preprint.date_published.strftime('%Y-%m-%d')),
                xmlns=CROSSREF_ACCESS_INDICATORS
            )
        )

    if preprint.node.preprint_article_doi:
        posted_content.append(
            element.program(
                element.related_item(
                    element.intra_work_relation(
                        preprint.node.preprint_article_doi,
                        **{'relationship-type': 'isPreprintOf', 'identifier-type': 'doi'}
                    ),
                    xmlns=CROSSREF_RELATIONS
                )
            )
        )

    doi_data = [
        element.doi(doi),
        element.resource(settings.DOMAIN + preprint._id)
    ]
    posted_content.append(element.doi_data(*doi_data))

    root = element.doi_batch(
        head,
        element.body(posted_content),
        version=CROSSREF_SCHEMA_VERSION
    )

    # set xsi:schemaLocation
    root.attrib['{%s}schemaLocation' % XSI] = CROSSREF_SCHEMA_LOCATION
    return lxml.etree.tostring(root, pretty_print=pretty_print)


# This function is OSF specific.
def datacite_metadata_for_preprint(preprint, doi, pretty_print=False):
    """Return the datacite metadata XML document for a given preprint as a string.

    :param preprint -- the preprint
    :param str doi
    """
    # NOTE: If you change *ANYTHING* here be 100% certain that the
    # changes you make are also made to the SHARE serialization code.
    # If the data sent out is not EXCATLY the same all the data will get jumbled up in SHARE.
    # And then search results will be wrong and broken. And it will be your fault. And you'll have caused many sleepless nights.
    # Don't be that person.
    root = E.resource(
        E.resourceType('Preprint', resourceTypeGeneral='Text'),
        E.identifier(doi, identifierType='DOI'),
        E.subjects(*format_subjects(preprint)),
        E.creators(*format_creators(preprint)),
        E.titles(E.title(remove_control_characters(preprint.node.title))),
        E.publisher(preprint.provider.name),
        E.publicationYear(str(getattr(preprint.date_published, 'year'))),
        E.dates(E.date(preprint.modified.isoformat(), dateType='Updated')),
        E.alternateIdentifiers(E.alternateIdentifier(settings.DOMAIN + preprint._id, alternateIdentifierType='URL')),
        E.descriptions(E.description(remove_control_characters(preprint.node.description), descriptionType='Abstract')),
    )

    if preprint.license:
        root.append(E.rightsList(E.rights(preprint.license.name)))

    if preprint.article_doi:
        root.append(E.relatedIdentifiers(E.relatedIdentifier(DOI_URL_PREFIX + preprint.article_doi, relatedIdentifierType='URL', relationType='IsPreviousVersionOf'))),
    # set xsi:schemaLocation
    root.attrib['{%s}schemaLocation' % XSI] = SCHEMA_LOCATION
    return lxml.etree.tostring(root, pretty_print=pretty_print)
