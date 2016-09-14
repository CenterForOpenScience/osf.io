# -*- coding: utf-8 -*-
import lxml.etree
import lxml.builder

NAMESPACE = 'http://datacite.org/schema/kernel-3'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
SCHEMA_LOCATION = 'http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd'
E = lxml.builder.ElementMaker(nsmap={
    None: NAMESPACE,
    'xsi': XSI},
)

CREATOR = E.creator
CREATOR_NAME = E.creatorName


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
        E.identifier(doi, identifierType='DOI'),
        E.creators(*creators),
        E.titles(E.title(title)),
        E.publisher(publisher),
        E.publicationYear(str(publication_year)),
    )
    # set xsi:schemaLocation
    root.attrib['{%s}schemaLocation' % XSI] = SCHEMA_LOCATION
    return lxml.etree.tostring(root, pretty_print=pretty_print)


# This function is OSF specific.
def datacite_metadata_for_node(node, doi, pretty_print=False):
    """Return the datacite metadata XML document for a given node as a string.

    :param Node node
    :param str doi
    """
    def format_contrib(contributor):
        return u'{}, {}'.format(contributor.family_name, contributor.given_name)
    creators = [format_contrib(each)
                for each in node.visible_contributors]
    return datacite_metadata(
        doi=doi,
        title=node.title,
        creators=creators,
        publisher='Open Science Framework',
        publication_year=getattr(node.registered_date or node.date_created, 'year'),
        pretty_print=pretty_print
    )
