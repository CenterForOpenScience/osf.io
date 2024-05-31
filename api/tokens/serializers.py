from rest_framework import serializers as ser
from rest_framework import exceptions

from osf.exceptions import ValidationError
from osf.models import ApiOAuth2PersonalToken, ApiOAuth2Scope

from api.base.exceptions import format_validation_error
from api.base.serializers import JSONAPISerializer, LinksField, IDField, TypeField, RelationshipField
from packaging.version import Version
from api.scopes.serializers import SCOPES_RELATIONSHIP_VERSION


class ApiOAuth2PersonalTokenSerializer(JSONAPISerializer):
    """Serialize data about a registered personal access token"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = kwargs['context']['request']

        # Dynamically adding scopes field here, depending on the version
        if expect_scopes_as_relationships(request):
            field = RelationshipField(
                related_view='tokens:token-scopes-list',
                related_view_kwargs={'_id': '<_id>'},
                always_embed=True,
                read_only=False,
            )
            self.fields['scopes'] = field
            self.fields['owner'] = RelationshipField(
                related_view='users:user-detail',
                related_view_kwargs={'user_id': '<owner._id>'},
            )
            # Making scopes embeddable
            self.context['embed']['scopes'] = self.context['view']._get_embed_partial('scopes', field)
        else:
            self.fields['scopes'] = ser.SerializerMethodField()
            self.fields['owner'] = ser.SerializerMethodField()

    id = IDField(source='_id', read_only=True, help_text='The object ID for this token (automatically generated)')
    type = TypeField()

    name = ser.CharField(
        help_text='A short, descriptive name for this token',
        required=True,
    )

    token_id = ser.CharField(read_only=True, allow_blank=True)

    class Meta:
        type_ = 'tokens'

    links = LinksField({
        'html': 'absolute_url',
    })

    def get_owner(self, obj):
        return obj.owner._id

    def get_scopes(self, obj):
        return ' '.join([scope.name for scope in obj.scopes.all()])

    def absolute_url(self, obj):
        return obj.absolute_url

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def to_representation(self, obj, envelope='data'):
        data = super().to_representation(obj, envelope=envelope)
        # Make sure users only see token_id on create
        if not self.context['request'].method == 'POST':
            if 'data' in data:
                data['data']['attributes'].pop('token_id')
            else:
                data['attributes'].pop('token_id')

        return data

    def create(self, validated_data):
        scopes = validate_requested_scopes(validated_data.pop('scopes', None))
        if not scopes:
            raise exceptions.ValidationError('Cannot create a token without scopes.')
        instance = ApiOAuth2PersonalToken(**validated_data)
        try:
            instance.save()
        except ValidationError as e:
            detail = format_validation_error(e)
            raise exceptions.ValidationError(detail=detail)
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
        try:
            instance.save()
        except ValidationError as e:
            detail = format_validation_error(e)
            raise exceptions.ValidationError(detail=detail)
        return instance


class ApiOAuth2PersonalTokenWritableSerializer(ApiOAuth2PersonalTokenSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs['context']['request']

        # Dynamically overriding scopes field for early versions to make scopes writable via an attribute
        if not expect_scopes_as_relationships(request):
            self.fields['scopes'] = ser.CharField(write_only=True, required=False)

    def to_representation(self, obj, envelope='data'):
        """
        Overriding to_representation allows using different serializers for the request and response.

        This will allow scopes to be a serializer method field if an early version, or a relationship field for a later version
        """
        context = self.context
        return ApiOAuth2PersonalTokenSerializer(instance=obj, context=context).data


def expect_scopes_as_relationships(request):
    """Whether serializer should expect scopes to be a relationship instead of an attribute

    Scopes were previously an attribute on the serializer to mirror that they were a CharField on the model.
    Now that scopes are an m2m field with tokens, later versions of the serializer represent scopes as relationships.
    """
    return Version(getattr(request, 'version', '2.0')) >= Version(SCOPES_RELATIONSHIP_VERSION)

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

    if not isinstance(data, list):
        data = data.split(' ')
    scopes = ApiOAuth2Scope.objects.filter(name__in=data)

    if len(scopes) != len(data):
        raise exceptions.NotFound(
            'Scope names must be one of: {}.'.format(
                ', '.join(ApiOAuth2Scope.objects.values_list('name', flat=True)),
            ),
        )

    if scopes.filter(is_public=False):
        raise exceptions.ValidationError('User requested invalid scope.')

    return scopes
