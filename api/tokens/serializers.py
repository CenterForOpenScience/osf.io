from rest_framework import serializers as ser
from rest_framework import exceptions

from osf.models import ApiOAuth2PersonalToken, ApiOAuth2Scope

from api.base.serializers import JSONAPISerializer, LinksField, IDField, TypeField, RelationshipField


class TokenScopesRelationshipField(RelationshipField):

    def to_internal_value(self, data):
        return {'scopes': data}


class ApiOAuth2PersonalTokenSerializer(JSONAPISerializer):
    """Serialize data about a registered personal access token"""

    id = IDField(source='_id', read_only=True, help_text='The object ID for this token (automatically generated)')
    type = TypeField()

    name = ser.CharField(
        help_text='A short, descriptive name for this token',
        required=True,
    )

    # TODO VERSION
    # owner = ser.CharField(
    #     help_text='The user who owns this token',
    #     read_only=True,  # Don't let user register a token in someone else's name
    #     source='owner._id',
    # )

    # TODO VERSION w/ serializer method field
    # scopes = ser.CharField(
    #     help_text='Governs permissions associated with this token',
    #     required=True,
    # )

    token_id = ser.CharField(read_only=True, allow_blank=True)

    class Meta:
        type_ = 'tokens'

    links = LinksField({
        'html': 'absolute_url',
    })

    owner = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<owner._id>'},
    )

    scopes = TokenScopesRelationshipField(
        related_view='tokens:token-scopes-list',
        related_view_kwargs={'_id': '<_id>'},
        always_embed=True,
        read_only=False,
    )

    def absolute_url(self, obj):
        return obj.absolute_url

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def to_representation(self, obj, envelope='data'):
        data = super(ApiOAuth2PersonalTokenSerializer, self).to_representation(obj, envelope=envelope)
        # Make sure users only see token_id on create
        if not self.context['request'].method == 'POST':
            if 'data' in data:
                data['data']['attributes'].pop('token_id')
            else:
                data['attributes'].pop('token_id')

        return data

    def create(self, validated_data):
        scopes = validate_requested_scopes(validated_data.pop('scopes', None))
        instance = ApiOAuth2PersonalToken(**validated_data)
        instance.save()
        for scope in scopes:
            instance.scopes.add(scope)
        return instance

    def update(self, instance, validated_data):
        scopes = validate_requested_scopes(validated_data.pop('scopes', None))
        assert isinstance(instance, ApiOAuth2PersonalToken), 'instance must be an ApiOAuth2PersonalToken'

        instance.deactivate(save=False)  # This will cause CAS to revoke the existing token but still allow it to be used in the future, new scopes will be updated properly at that time.
        instance.reload()

        for attr, value in validated_data.items():
            if attr == 'token_id':  # Do not allow user to update token_id
                continue
            else:
                setattr(instance, attr, value)
        if scopes:
            update_scopes(instance, scopes)

        instance.save()
        return instance

def update_scopes(token, scopes):
    to_remove = token.scopes.difference(scopes)
    to_add = scopes.difference(token.scopes.all())
    for scope in to_remove:
        token.scopes.remove(scope)
    for scope in to_add:
        token.scopes.add(scope)
    return

def validate_requested_scopes(data):
    if not data:
        return []
    scopes = ApiOAuth2Scope.objects.filter(name__in=data)
    if len(scopes) != len(data):
        raise exceptions.NotFound

    if scopes.filter(is_public=False):
        raise exceptions.ValidationError('User requested invalid scope')
    return scopes
