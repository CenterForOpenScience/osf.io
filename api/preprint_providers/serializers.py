from guardian.shortcuts import get_perms
from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from api.actions.serializers import ReviewableCountsRelationshipField
from api.base.utils import absolute_reverse, get_user_auth
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField, ShowIfVersion
from api.preprint_providers.workflows import Workflows


class PreprintProviderSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'allow_submissions',
        'description',
        'domain',
        'domain_redirect_enabled',
        'id',
        'name',
        'share_publish_type',
        'reviews_workflow',
        'permissions',
    ])

    name = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    id = ser.CharField(read_only=True, max_length=200, source='_id')
    advisory_board = ser.CharField(read_only=True)
    example = ser.CharField(read_only=True, allow_null=True)
    domain = ser.CharField(read_only=True, allow_null=False)
    domain_redirect_enabled = ser.BooleanField(read_only=True)
    footer_links = ser.CharField(read_only=True)
    share_source = ser.CharField(read_only=True)
    share_publish_type = ser.CharField(read_only=True)
    email_support = ser.CharField(read_only=True, allow_null=True)
    preprint_word = ser.CharField(read_only=True, allow_null=True)
    allow_submissions = ser.BooleanField(read_only=True)
    additional_providers = ser.ListField(read_only=True, child=ser.CharField())

    # Reviews settings are the only writable fields
    reviews_workflow = ser.ChoiceField(choices=Workflows.choices())
    reviews_comments_private = ser.BooleanField()
    reviews_comments_anonymous = ser.BooleanField()

    permissions = ser.SerializerMethodField()

    preprints = ReviewableCountsRelationshipField(
        related_view='preprint_providers:preprints-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    taxonomies = RelationshipField(
        related_view='preprint_providers:taxonomy-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    highlighted_taxonomies = RelationshipField(
        related_view='preprint_providers:highlighted-taxonomy-list',
        related_view_kwargs={'provider_id': '<_id>'},
        related_meta={'has_highlighted_subjects': 'get_has_highlighted_subjects'}
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
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.3'
    )
    banner_path = ShowIfVersion(
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.3'
    )
    logo_path = ShowIfVersion(
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.3'
    )
    email_contact = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    social_twitter = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    social_facebook = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    social_instagram = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3'
    )
    subjects_acceptable = ShowIfVersion(
        ser.ListField(read_only=True, default=[]),
        min_version='2.0', max_version='2.4'
    )

    class Meta:
        type_ = 'preprint_providers'

    def get_has_highlighted_subjects(self, obj):
        return obj.has_highlighted_subjects

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_preprints_url(self, obj):
        return absolute_reverse('preprint_providers:preprints-list', kwargs={
            'provider_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_external_url(self, obj):
        return obj.external_url

    def get_permissions(self, obj):
        auth = get_user_auth(self.context['request'])
        if not auth.user:
            return []
        return get_perms(auth.user, obj)

    def validate(self, data):
        required_fields = ('reviews_workflow', 'reviews_comments_private', 'reviews_comments_anonymous')
        for field in required_fields:
            if data.get(field) is None:
                raise ValidationError('All reviews fields must be set at once: `{}`'.format('`, `'.join(required_fields)))
        return data

    def update(self, instance, validated_data):
        instance.reviews_workflow = validated_data['reviews_workflow']
        instance.reviews_comments_private = validated_data['reviews_comments_private']
        instance.reviews_comments_anonymous = validated_data['reviews_comments_anonymous']
        instance.save()
        return instance
