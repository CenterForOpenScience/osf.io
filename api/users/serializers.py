from ast import literal_eval

from rest_framework import serializers as ser
from rest_framework.serializers import empty

from api.base.serializers import JSONAPISerializer, JSONAPIListSerializer, LinksField, Link
from website.models import User
from django.db import models
from jsonfield import JSONField
from django.utils import six, timezone
import inspect
from rest_framework.utils import html
import json
from rest_framework.parsers import JSONParser


class JobsSerializer(ser.ListField):
    startYear = ser.CharField(allow_blank=True, allow_null=True)
    title = ser.CharField()
    startMonth = ser.IntegerField(allow_null=True)
    endMonth = ser.IntegerField(max_value=12, min_value=1, allow_null=True)
    endYear = ser.CharField(allow_blank=True, allow_null=True)
    ongoing = ser.BooleanField()
    department = ser.CharField()
    institution = ser.CharField()

    class Meta:
        type_ = 'jobs'


class SchoolsSerializer(ser.ListField):
    startYear = ser.CharField(allow_blank=True, allow_null=True)
    degree = ser.CharField()
    startMonth = ser.IntegerField(max_value=12, min_value=1, allow_null=True)
    endMonth = ser.IntegerField(max_value=12, min_value=1, allow_null=True)
    endYear = ser.CharField(allow_blank=True, allow_null=True)
    ongoing = ser.BooleanField()
    department = ser.CharField()
    institution = ser.CharField()

    class Meta:
        type_ = 'schools'


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_name',
        'family_name',
        'id'
    ])
    parser_classes = (JSONParser,)
    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField(help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, help_text='For bibliographic citations')
    middle_name = ser.CharField(required=False, source='middle_names', help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, help_text='For bibliographic citations')
    suffix = ser.CharField(required=False, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.CharField(required=False, help_text='URL for the icon used to identify the user. Relies on http://gravatar.com ')
    employment_institutions = JobsSerializer(read_only=True, required=False, source='jobs', help_text='An array of dictionaries representing the '
                                                                     'places the user has worked')
    # employment_institutions = ser.ListField(read_only=True, required=False, source='jobs', help_text='An array of dictionaries representing the '
    #                                                                  'places the user has worked')
    educational_institutions = SchoolsSerializer(read_only=True, required=False, source='schools', help_text='An array of dictionaries representing the '
                                                                     'places the user has worked')
    # educational_institutions = ser.ListField(read_only=True, child=ser.CharField(), required=False, source='schools', help_text='An array of dictionaries representing the '
    #                                                                      'places the user has attended school')

    github = ser.CharField(required=False, source='social.github', help_text='Github Handle')
    scholar = ser.CharField(required=False, source='social.scholar', help_text='Google Scholar Account')
    personal_website = ser.CharField(required=False, source='social.personal', help_text='Personal Website')
    twitter = ser.CharField(required=False, source='social.twitter', help_text='Twitter Handle')
    linkedIn = ser.CharField(required=False, source='social.linkedIn', help_text='LinkedIn Account')
    impactStory = ser.CharField(required=False, source='social.impactStory', help_text='ImpactStory Account')
    orcid = ser.CharField(required=False, source='social.orcid', help_text='orcid Account Number ex 1111 1111 1111 1111')
    researcherId = ser.CharField(required=False, source='social.researcherId', help_text='ResearcherId Account')

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'user_id': '<pk>'})
        }
    })

    class Meta:
        type_ = 'users'
        fields = ('id', 'fullname', 'given_name', 'middle_name', 'family_name', 'suffix', 'date_registered', 'gravatar_url', 'employment_institutions', 'social_accounts')

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        # jobs_data = validated_data.pop('jobs')
        # jobs = instance.jobs
        assert isinstance(instance, User), 'instance must be a User'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # jobs.save()
        instance.save()
        return instance


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
