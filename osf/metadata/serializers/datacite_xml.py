from datacite import schema43

from osf.metadata import gather
from osf.metadata.serializers import _base, datacite_json


class DataciteXmlMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'application/xml'

    def filename(self, osfguid: str):
        return f'{osfguid}-datacite.xml'

    def serialize(self, basket: gather.Basket):
        json_serializer = datacite_json.DataciteJsonMetadataSerializer(
            serializer_config={
                'doi_value': self.serializer_config.get('doi_value'),
            }
        )
        json_data = json_serializer.primitivize(basket)

        # Generate DataCite XML from dictionary.
        return schema43.tostring(json_data)
