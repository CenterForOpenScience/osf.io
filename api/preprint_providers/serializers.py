from rest_framework import serializers as ser

from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField, ShowIfVersion
from api.users.serializers import EmailSerializer, SocialAccountSerializer

from osf.models.preprint_provider import PreprintProviderLink


class PreprintProviderLinkSerializer(ser.ModelSerializer):

    class Meta:
        model = PreprintProviderLink
        fields = ('url', 'description', 'linked_text',)


class PreprintProviderSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'name',
        'description',
        'id'
    ])

    name = ser.CharField(required=True)
    description = ser.CharField(required=False)
    id = ser.CharField(max_length=200, source='_id')
    advisory_board = ser.CharField(required=False, allow_null=True)
    example = ser.CharField(required=False, allow_null=True)
    header_text = ser.CharField(required=False, allow_null=True)
    subjects_acceptable = ser.JSONField(required=False, allow_null=True)
    logo_path = ser.CharField(read_only=True)
    banner_path = ser.CharField(read_only=True)
    emails = EmailSerializer(read_only=True, many=True)
    social_accounts = SocialAccountSerializer(read_only=True, many=True)
    preprint_provider_links = PreprintProviderLinkSerializer(read_only=True, many=True, source='links')

    email_contact = ShowIfVersion(
        ser.CharField(required=False, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    email_support = ShowIfVersion(
        ser.CharField(required=False, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    social_twitter = ShowIfVersion(
        ser.CharField(required=False, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    social_facebook = ShowIfVersion(
        ser.CharField(required=False, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    social_instagram = ShowIfVersion(
        ser.CharField(required=False, allow_null=True),
        min_version='2.0', max_version='2.3'
    )

    preprints = RelationshipField(
        related_view='preprint_providers:preprints-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    taxonomies = RelationshipField(
        related_view='preprint_providers:taxonomy-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    licenses_acceptable = RelationshipField(
        related_view='preprint_providers:license-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'preprints': 'get_preprints_url',
        'external_url': 'get_external_url'
    })

    class Meta:
        type_ = 'preprint_providers'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_preprints_url(self, obj):
        return absolute_reverse('preprint_providers:preprints-list', kwargs={
            'provider_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_external_url(self, obj):
        # TODO: get from preprint_provider.links object
        return obj.external_url
