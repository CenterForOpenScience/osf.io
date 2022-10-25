import rest_framework.serializers as ser

from api.nodes.serializers import NodeSerializer


MAX_TYPE_LENGTH = 2**6  # 64
MAX_KEYWORD_LENGTH = 2**7  # 128
MAX_TITLE_LENGTH = 2**9  # 512
MAX_DESCRIPTION_LENGTH = 2**17  # 131072


class BaseEditableMetadataSerializer(ser.Serializer):
    title = ser.CharField(max_length=MAX_TITLE_LENGTH)
    description = ser.CharField(max_length=MAX_DESCRIPTION_LENGTH)
    # resourceTypeGeneral = ser.CharField()  # TODO: choices
    # resourceTypeSpecific = ser.CharField(max_length=MAX_TYPE_LENGTH)

    def update(self, instance, validated_data):
        inner_serializer = NodeSerializer(instance, data=validated_data, partial=True)
        inner_serializer.save()
        return instance


class NodeEditableMetadataSerializer(BaseEditableMetadataSerializer):
    INNER_SERIALIZER_CLASS = NodeSerializer


class JSONAPILDSerializer(ser.BaseSerializer):
    def to_representation(self, graph):
        focus_guid_irl = self.context['focus_guid_irl']
        # TODO: build json:api-style dict

    def to_internal_value(self, data):
        # TODO: rdflib.Graph().parse()
        raise NotImplementedError


class UpdatableJSONAPILDSerializer(JSONAPILDSerializer):
    def update(self, validated_data):
        # pull out the specifically writable fields:
        raise NotImplementedError
