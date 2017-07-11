from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, DateByVersion


class CitationSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'title',
        'short_title',
        'summary',
        'id'
    ])
    id = ser.CharField(source='_id', required=True)
    title = ser.CharField(max_length=200)
    date_parsed = DateByVersion(read_only=True, help_text='Datetime the csl file was last parsed')

    short_title = ser.CharField(max_length=500)
    summary = ser.CharField(max_length=200)

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'citation-styles'
