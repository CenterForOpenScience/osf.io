from rest_framework import serializers
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


# JSON Serializers for /export_{process_start}/export_data_{institution_guid}_{process_start}.json
class InstitutionSerializer(serializers.Serializer):
    institution_id = serializers.IntegerField(required=True)
    institution_guid = serializers.CharField(required=True)
    institution_name = serializers.CharField(required=True)


class StorageSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    type = serializers.CharField(required=True)


class ExportDataSerializer(serializers.Serializer):
    institution = InstitutionSerializer()
    process_start = serializers.DateTimeField(required=True, format=DATETIME_FORMAT)
    process_end = serializers.DateTimeField(required=True, format=DATETIME_FORMAT)
    storage = StorageSerializer()
    projects_numb = serializers.IntegerField(required=True, min_value=0)
    files_numb = serializers.IntegerField(required=True, min_value=0)
    size = serializers.IntegerField(required=True, min_value=0)
    file_path = serializers.CharField(required=True)


class FileInfoSerializer(serializers.Serializer):
    institution = InstitutionSerializer()
    # TODO: complete fields
