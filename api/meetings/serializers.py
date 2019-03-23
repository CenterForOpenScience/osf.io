from rest_framework import serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)


class MeetingSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(read_only=True)
    location = ser.CharField(read_only=True)
    start_date = VersionedDateTimeField(read_only=True)
    end_date = VersionedDateTimeField(read_only=True)

    submissions = RelationshipField(
        related_view='meetings:meeting-submissions',
        related_view_kwargs={'meeting_id': '<_id>'},
        related_meta={'count': 'get_submissions_count'},
    )

    links = LinksField({
        'self': 'get_api_url',
        'html': 'get_absolute_html_url',
    })

    def get_submissions_count(self, obj):
        # TODO - optimize.  Annotate queryset with submission count
        view = self.context['view']
        return view.get_submissions().count()

    def get_api_url(self, obj):
        return obj.absolute_api_v2_url

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'meetings'
