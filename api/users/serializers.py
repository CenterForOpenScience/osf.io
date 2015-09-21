from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from website.models import User

from api.base.exceptions import Conflict
from api.base.utils import enforce_type_and_id_and_pop_attributes
from api.base.serializers import (
    JSONAPISerializer, LinksField, JSONAPIHyperlinkedIdentityField, DevOnly
)


class UserAttributesSerializer(JSONAPISerializer):

    fullname = ser.CharField(required=True, label='Full name', help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    middle_names = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    suffix = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)

    # Social Fields are broken out to get around DRF complex object bug and to make API updating more user friendly.
    gitHub = DevOnly(ser.CharField(required=False, label='GitHub', source='social.github', allow_blank=True, help_text='GitHub Handle'))
    scholar = DevOnly(ser.CharField(required=False, source='social.scholar', allow_blank=True, help_text='Google Scholar Account'))
    personal_website = DevOnly(ser.URLField(required=False, source='social.personal', allow_blank=True, help_text='Personal Website'))
    twitter = DevOnly(ser.CharField(required=False, source='social.twitter', allow_blank=True, help_text='Twitter Handle'))
    linkedIn = DevOnly(ser.CharField(required=False, source='social.linkedIn', allow_blank=True, help_text='LinkedIn Account'))
    impactStory = DevOnly(ser.CharField(required=False, source='social.impactStory', allow_blank=True, help_text='ImpactStory Account'))
    orcid = DevOnly(ser.CharField(required=False, label='ORCID', source='social.orcid', allow_blank=True, help_text='ORCID'))
    researcherId = DevOnly(ser.CharField(required=False, label='ResearcherID', source='social.researcherId', allow_blank=True, help_text='ResearcherId Account'))

    # Overrides JSONAPISerializer
    def get_attribute(self, instance):
        attribute = {}
        for field in self.fields:
            if self.fields[field].write_only:
                continue

            field_name = self.fields[field].source

            if 'social' in field_name:
                soc = field_name.split('.')[1]
                social = getattr(instance, 'social')
                lookup = social.get(soc)
            else:
                lookup = getattr(instance, field_name)

            if lookup is None:
                attribute[field] = None
            else:
                attribute[field] = self.fields[field].to_representation(lookup)
        return attribute

    # Overrides JSONAPISerializer
    def to_representation(self, value):
        """
        Dictionary representation
        """
        return value


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
    attributes = UserAttributesSerializer()
    profile_image_url = DevOnly(ser.SerializerMethodField(required=False, read_only=True))

    def get_profile_image_url(self, user):
        size = self.context['request'].query_params.get('profile_image_size')
        return user.profile_image_url(size=size)

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
        validated_data = enforce_type_and_id_and_pop_attributes(validated_data)

        assert isinstance(instance, User), 'instance must be a User'
        for attr, value in validated_data.items():
            if 'social' == attr:
                for key, val in value.items():
                    instance.social[key] = val
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance


class UserUpdateSerializer(UserSerializer):
    """
    Overrides UserSerializer to make id required and validate id.
    """
    id = ser.CharField(source='_id', label='ID', required=True)

    def validate_id(self, value):
        if self._args[0]._id != value:
            raise Conflict()
        return value


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
