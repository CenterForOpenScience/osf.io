from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from website.models import User

from api.base.exceptions import Conflict
from api.base.serializers import JSONAPISerializer, LinksField, JSONAPIHyperlinkedIdentityField

class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_names',
        'family_name',
        'id'
    ])
    id = ser.CharField(read_only=True, source='_id', label='ID')
    type = ser.CharField(write_only=True, required=True)
    fullname = ser.CharField(required=True, label='Full name', help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    middle_names = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    suffix = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)

    profile_image_url = ser.SerializerMethodField(required=False, read_only=True)

    def get_profile_image_url(self, user):
        size = self.context['request'].query_params.get('profile_image_size')
        return user.profile_image_url(size=size)

    # Social Fields are broken out to get around DRF complex object bug and to make API updating more user friendly.
    gitHub = ser.CharField(required=False, label='GitHub', source='social.github', allow_blank=True, help_text='GitHub Handle')
    scholar = ser.CharField(required=False, source='social.scholar', allow_blank=True, help_text='Google Scholar Account')
    personal_website = ser.URLField(required=False, source='social.personal', allow_blank=True, help_text='Personal Website')
    twitter = ser.CharField(required=False, source='social.twitter', allow_blank=True, help_text='Twitter Handle')
    linkedIn = ser.CharField(required=False, source='social.linkedIn', allow_blank=True, help_text='LinkedIn Account')
    impactStory = ser.CharField(required=False, source='social.impactStory', allow_blank=True, help_text='ImpactStory Account')
    orcid = ser.CharField(required=False, label='ORCID', source='social.orcid', allow_blank=True, help_text='ORCID')
    researcherId = ser.CharField(required=False, label='ResearcherID', source='social.researcherId', allow_blank=True, help_text='ResearcherId Account')

    links = LinksField({'html': 'absolute_url'})
    nodes = JSONAPIHyperlinkedIdentityField(view_name='users:user-nodes', lookup_field='pk', lookup_url_kwarg='user_id',
                                             link_type='related')

    class Meta:
        type_ = 'users'

    def validate_type(self, value):
        if self.Meta.type_ != value:
            raise Conflict()
        return value

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        validated_id = validated_data.get('id', None)
        if not validated_id:
            validated_id = validated_data.get('_id', None)
        validated_type = validated_data.get('type', None)

        errors = {}
        if not validated_id:
            errors['id'] = ['This field is required.']
        if not validated_type:
            errors['type'] = ['This field is required.']

        if errors:
            raise ValidationError(errors)

        assert isinstance(instance, User), 'instance must be a User'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserUpdateSerializer(UserSerializer):
    id = ser.CharField(source='_id', label='ID', required=True)

    def validate_id(self, value):
        if self._args[0]._id != value:
            raise Conflict()
        return value


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
