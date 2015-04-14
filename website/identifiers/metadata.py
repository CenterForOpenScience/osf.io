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

def datacite_metadata_for_node(node, doi, pretty_print=False):
    """Return the datacite metadata XML document for a given node as a string."""
    def format_contrib(contributor):
        return u'{}, {}'.format(contributor.family_name, contributor.given_name)
    creators = [CREATOR(CREATOR_NAME(format_contrib(each)))
                        for each in node.visible_contributors]
    root = E.resource(
        E.identifier(doi, identifierType='DOI'),
        E.creators(*creators),
        E.titles(E.title(node.title)),
        E.publisher('OSF'),
        E.publicationYear(str(node.registered_date.year)),
    )
    root.attrib["{" + XSI + "}schemaLocation"] = SCHEMA_LOCATION
    return lxml.etree.tostring(root, pretty_print=pretty_print)
