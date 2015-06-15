from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link
from website.models import User

# class SocialFieldsSerializer(ser.Serializer):
#     github = ser.CharField()
#     scholar = ser.CharField()
#     personal = ser.CharField()
#     twitter = ser.CharField()
#     linkedIn = ser.CharField()
#     impactStory = ser.CharField()
#     orcid = ser.CharField()
#     researcherId = ser.CharField()


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_name',
        'family_name',
        'id'
    ])

    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField(help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, help_text='For bibliographic citations')
    middle_name = ser.CharField(required=False, source='middle_names', help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, help_text='For bibliographic citations')
    suffix = ser.CharField(required=False, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.CharField(required=False, help_text='URL for the icon used to identify the user. Relies on http://gravatar.com ')
    employment_institutions = ser.ListField(required=False, allow_null=True, source='jobs', help_text='An array of dictionaries representing the '
                                                                     'places the user has worked')
    educational_institutions = ser.ListField(required=False, allow_null=True, source='schools', help_text='An array of dictionaries representing the '
                                                                         'places the user has attended school')
    social_accounts = ser.DictField(child=ser.CharField(), required=False, source='social', help_text='A dictionary of various social media account '
                                                               'identifiers including an array of user-defined URLs')
    # social_accounts = SocialFieldsSerializer

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'pk': '<pk>'})
        }
    })

    class Meta:
        type_ = 'users'

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        assert isinstance(instance, User), 'instance must be a User'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
