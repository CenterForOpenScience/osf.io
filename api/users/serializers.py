from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField, Link, CharFieldWithReadDefault, URLFieldWithReadDefault
from website.models import User


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_names',
        'family_name',
        'id'
    ])
    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField(required=True, help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    middle_names = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    suffix = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.URLField(required=False, read_only=True,
                                help_text='URL for the icon used to identify the user. Relies on http://gravatar.com ')

    # Social Fields are broken out to get around DRF complex object bug and to make API updating more user friendly.
    gitHub = CharFieldWithReadDefault(required=False, source='social.github',
                                      allow_blank=True, help_text='GitHub Handle')
    scholar = CharFieldWithReadDefault(required=False, source='social.scholar',
                                       allow_blank=True, help_text='Google Scholar Account')
    personal_website = URLFieldWithReadDefault(required=False, source='social.personal',
                                               allow_blank=True, help_text='Personal Website')
    twitter = CharFieldWithReadDefault(required=False, source='social.twitter',
                                       allow_blank=True, help_text='Twitter Handle')
    linkedIn = CharFieldWithReadDefault(required=False, source='social.linkedIn',
                                        allow_blank=True, help_text='LinkedIn Account')
    impactStory = CharFieldWithReadDefault(required=False, source='social.impactStory',
                                           allow_blank=True, help_text='ImpactStory Account')
    orcid = CharFieldWithReadDefault(required=False, source='social.orcid',
                                     allow_blank=True, help_text='ORCID')
    researcherId = CharFieldWithReadDefault(required=False, source='social.researcherId',
                                            allow_blank=True, help_text='ResearcherId Account')

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'user_id': '<pk>'})
        }
    })

    class Meta:
        type_ = 'users'

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        assert isinstance(instance, User), 'instance must be a User'
        for attr, value in validated_data.items():
            # If the field is the social dictionary, then update the original social values with the new ones, and save.
            # If its any other field, just update with the value.
            if attr == 'social':
                social_fields = instance.social
                social_fields.update(value)
                setattr(instance, attr, social_fields)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
