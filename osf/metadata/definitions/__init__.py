import abc
import pathlib

from lxml import etree


class BaseMetadataDefinition(abc.ABC):
    @abc.abstractmethod
    def raise_objections(self, metadata_record) -> None:
        raise NotImplementedError


class BaseXmlschemaDefinition(BaseMetadataDefinition):
    @classmethod
    @abc.abstractmethod
    def xmlschema_file_path(self):
        raise NotImplementedError

    @classmethod
    def xmlschema(cls):
        try:
            return cls._xmlschema_cache
        except AttributeError:
            with open(cls.xmlschema_file_path()) as xsd_file:
                xsd_tree = etree.parse(xsd_file)
            cls._xmlschema_cache = etree.XMLSchema(xsd_tree)
            return cls._xmlschema_cache

    def raise_objections(self, metadata_record):
        xml_doc = (
            metadata_record
            if isinstance(metadata_record, (etree._Element, etree._ElementTree))
            else etree.parse(metadata_record)
        )
        self.xmlschema().assertValid(xml_doc)


class DataciteXmlschemaDefinition(BaseXmlschemaDefinition):
    @classmethod
    def xmlschema_file_path(self):
        return (
            pathlib.Path(__file__)
            .parent
            .joinpath('datacite', 'datacite-v4.xsd')
        )
