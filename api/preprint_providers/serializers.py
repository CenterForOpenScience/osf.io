from rest_framework import serializers as ser

from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField, ShowIfVersion


class PreprintProviderSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'allow_submissions',
        'description',
        'domain',
        'domain_redirect_enabled',
        'id',
        'name',
        'share_publish_type',
    ])

    name = ser.CharField(required=True)
    description = ser.CharField(required=False)
    id = ser.CharField(max_length=200, source='_id')
    advisory_board = ser.CharField(required=False)
    example = ser.CharField(required=False, allow_null=True)
    domain = ser.CharField(required=False, allow_null=False)
    domain_redirect_enabled = ser.BooleanField(required=True)
    footer_links = ser.CharField(required=False)
    share_source = ser.CharField(read_only=True)
    share_publish_type = ser.CharField(read_only=True)
    email_support = ser.CharField(required=False, allow_null=True)
    preprint_word = ser.CharField(required=False, allow_null=True)
    allow_submissions = ser.BooleanField(read_only=True)
    additional_providers = ser.ListField(child=ser.CharField(), read_only=True)

    preprints = RelationshipField(
        related_view='preprint_providers:preprints-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    taxonomies = RelationshipField(
        related_view='preprint_providers:taxonomy-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    highlighted_taxonomies = RelationshipField(
        related_view='preprint_providers:highlighted-taxonomy-list',
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

    # Deprecated fields
    header_text = ShowIfVersion(
        ser.CharField(required=False, default=''),
        min_version='2.0', max_version='2.3'
    )
    banner_path = ShowIfVersion(
        ser.CharField(required=False, default=''),
        min_version='2.0', max_version='2.3'
    )
    logo_path = ShowIfVersion(
        ser.CharField(required=False, default=''),
        min_version='2.0', max_version='2.3'
    )
    email_contact = ShowIfVersion(
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
    subjects_acceptable = ShowIfVersion(
        ser.ListField(required=False, default=[]),
        min_version='2.0', max_version='2.4'
    )

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
        return obj.external_url
