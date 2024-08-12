import logging

from lxml import etree

from osf.metadata.definitions import DataciteXmlschemaDefinition
from osf.metadata.serializers import _base
from .datacite_tree_walker import DataciteTreeWalker


logger = logging.getLogger(__name__)


XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
DATACITE_NAMESPACE = "http://datacite.org/schema/kernel-4"
DATACITE_XSD_URL = "http://schema.datacite.org/meta/kernel-4.5/metadata.xsd"
LANGUAGE_ATTRIB = etree.QName(XML_NAMESPACE, "lang")
SCHEMA_LOCATION_ATTRIB = etree.QName(XSI_NAMESPACE, "schemaLocation")
DATACITE_SCHEMA_LOCATION = " ".join((DATACITE_NAMESPACE, DATACITE_XSD_URL))


def _visit_tree_branch_xml(
    parent: etree._Element,
    tag_name: str,
    *,
    is_list=False,
    text=None,
    attrib=None,
):
    child = etree.SubElement(
        parent, etree.QName(DATACITE_NAMESPACE, tag_name), attrib=attrib or {}
    )
    if text is not None:
        child.text = text
        text_language = getattr(text, "language", None)
        if text_language:
            child.attrib[LANGUAGE_ATTRIB] = text_language
    return child


class DataciteXmlMetadataSerializer(_base.MetadataSerializer):
    mediatype = "application/xml"

    def filename_for_itemid(self, itemid):
        return f"{itemid}-datacite.xml"

    def serialize(self) -> bytes:
        xml_tree = self.metadata_as_etree()
        return etree.tostring(
            xml_tree,
            encoding="utf-8",
            pretty_print=True,
            xml_declaration=True,
        )

    def metadata_as_etree(self):
        xml_root = etree.Element(
            etree.QName(DATACITE_NAMESPACE, "resource"),
            attrib={
                SCHEMA_LOCATION_ATTRIB: DATACITE_SCHEMA_LOCATION,
            },
            nsmap={
                None: DATACITE_NAMESPACE,
                "xsi": XSI_NAMESPACE,
            },
        )
        walker = DataciteTreeWalker(
            self.basket, xml_root, _visit_tree_branch_xml
        )
        walker.walk(doi_override=self.serializer_config.get("doi_value"))
        xml_tree = etree.ElementTree(xml_root)
        DataciteXmlschemaDefinition().raise_objections(xml_tree)
        return xml_tree
