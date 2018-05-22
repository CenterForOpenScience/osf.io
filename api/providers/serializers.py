from guardian.shortcuts import get_perms
from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from api.actions.serializers import ReviewableCountsRelationshipField
from api.base.utils import absolute_reverse, get_user_auth
from api.base.serializers import JSONAPISerializer, IDField, LinksField, RelationshipField, TypeField, TypedRelationshipField
from api.providers.permissions import GROUPS
from api.providers.workflows import Workflows
from osf.models.user import Email, OSFUser
from osf.models.validators import validate_email
from website import mails
from website.settings import DOMAIN


class ProviderSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'providers'

    name = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    id = ser.CharField(read_only=True, max_length=200, source='_id')
    advisory_board = ser.CharField(read_only=True)
    example = ser.CharField(read_only=True, allow_null=True)
    domain = ser.CharField(read_only=True, allow_null=False)
    domain_redirect_enabled = ser.BooleanField(read_only=True)
    footer_links = ser.CharField(read_only=True)
    email_support = ser.CharField(read_only=True, allow_null=True)
    facebook_app_id = ser.IntegerField(read_only=True, allow_null=True)
    allow_submissions = ser.BooleanField(read_only=True)
    allow_commenting = ser.BooleanField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
        'external_url': 'get_external_url'
    })

    taxonomies = TypedRelationshipField(
        related_view='providers:taxonomy-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    highlighted_taxonomies = TypedRelationshipField(
        related_view='providers:highlighted-taxonomy-list',
        related_view_kwargs={'provider_id': '<_id>'},
        related_meta={'has_highlighted_subjects': 'get_has_highlighted_subjects'}
    )

    licenses_acceptable = TypedRelationshipField(
        related_view='providers:license-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    def get_has_highlighted_subjects(self, obj):
        return obj.has_highlighted_subjects

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_external_url(self, obj):
        return obj.external_url


class CollectionProviderSerializer(ProviderSerializer):
    class Meta:
        type_ = 'collection-providers'

    primary_collection = RelationshipField(
        related_view='collections:collection-detail',
        related_view_kwargs={'collection_id': '<primary_collection._id>'}
    )

    filterable_fields = frozenset([
        'allow_submissions',
        'allow_commenting',
        'description',
        'domain',
        'domain_redirect_enabled',
        'id',
        'name',
    ])

class PreprintProviderSerializer(ProviderSerializer):

    class Meta:
        type_ = 'preprint-providers'

    filterable_fields = frozenset([
        'allow_submissions',
        'allow_commenting',
        'description',
        'domain',
        'domain_redirect_enabled',
        'id',
        'name',
        'share_publish_type',
        'reviews_workflow',
        'permissions',
    ])

    share_source = ser.CharField(read_only=True)
    share_publish_type = ser.CharField(read_only=True)
    preprint_word = ser.CharField(read_only=True, allow_null=True)
    additional_providers = ser.ListField(read_only=True, child=ser.CharField())
    permissions = ser.SerializerMethodField()

    # Reviews settings are the only writable fields
    reviews_workflow = ser.ChoiceField(choices=Workflows.choices())
    reviews_comments_private = ser.BooleanField()
    reviews_comments_anonymous = ser.BooleanField()

    links = LinksField({
        'self': 'get_absolute_url',
        'preprints': 'get_preprints_url',
        'external_url': 'get_external_url'
    })

    preprints = ReviewableCountsRelationshipField(
        related_view='providers:preprint-providers:preprints-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    def get_preprints_url(self, obj):
        return absolute_reverse('providers:preprint-providers:preprints-list', kwargs={
            'provider_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

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


class ModeratorSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'full_name',
        'id',
        'permission_group'
    ])

    id = IDField(source='_id', required=False, allow_null=True)
    type = TypeField()
    full_name = ser.CharField(source='fullname', required=False, label='Full name', help_text='Display name used in the general user interface', max_length=186)
    permission_group = ser.CharField(required=True)
    email = ser.EmailField(required=False, write_only=True, validators=[validate_email])

    class Meta:
        type_ = 'moderators'

    def get_absolute_url(self, obj):
        return absolute_reverse('moderators:provider-moderator-detail', kwargs={
            'provider_id': self.context['request'].parser_context['kwargs']['version'],
            'moderator_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']})

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        user_id = validated_data.pop('_id', '')
        address = validated_data.pop('email', '')
        provider = self.context['provider']
        context = {
            'referrer': auth.user
        }
        if user_id and address:
            raise ValidationError('Cannot specify both "id" and "email".')

        user = None
        if user_id:
            user = OSFUser.load(user_id)
        elif address:
            try:
                email = Email.objects.get(address=address.lower())
            except Email.DoesNotExist:
                full_name = validated_data.pop('fullname', '')
                if not full_name:
                    raise ValidationError('"full_name" is required when adding a moderator via email.')
                user = OSFUser.create_unregistered(full_name, email=address)
                user.add_unclaimed_record(provider, referrer=auth.user,
                                                 given_name=full_name, email=address)
                user.save()
                claim_url = user.get_claim_url(provider._id, external=True)
                context['claim_url'] = claim_url
            else:
                user = email.user
        else:
            raise ValidationError('Must specify either "id" or "email".')

        if not user:
            raise ValidationError('Unable to find specified user.')
        context['user'] = user
        context['provider'] = provider

        if bool(get_perms(user, provider)):
            raise ValidationError('Specified user is already a moderator.')
        if 'claim_url' in context:
            template = mails.CONFIRM_EMAIL_MODERATION(provider)
        else:
            template = mails.MODERATOR_ADDED(provider)

        perm_group = validated_data.pop('permission_group', '')
        if perm_group not in GROUPS:
            raise ValidationError('Unrecognized permission_group')
        context['notification_settings_url'] = '{}reviews/preprints/{}/notifications'.format(DOMAIN, provider._id)
        context['provider_name'] = provider.name
        context['is_reviews_moderator_notificaiton'] = True
        context['is_admin'] = perm_group == 'admin'

        provider.add_to_group(user, perm_group)
        setattr(user, 'permission_group', perm_group)  # Allows reserialization
        mails.send_mail(
            user.username,
            template,
            mimetype='html',
            **context
        )
        return user

    def update(self, instance, validated_data):
        provider = self.context['provider']
        perm_group = validated_data.get('permission_group')
        if perm_group == instance.permission_group:
            return instance

        try:
            provider.remove_from_group(instance, instance.permission_group, unsubscribe=False)
        except ValueError as e:
            raise ValidationError(e.message)
        provider.add_to_group(instance, perm_group)
        setattr(instance, 'permission_group', perm_group)
        return instance
