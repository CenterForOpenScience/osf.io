from collections import OrderedDict
from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_name',
        'family_name',
        'id'
    ])
    id = ser.CharField(read_only=True, source='_id')
    attributes = ser.SerializerMethodField(help_text='A dictionary containing user properties')
    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'user_id': '<pk>'})
        }
    })

    class Meta:
        type_ = 'users'

    @staticmethod
    def get_attributes(obj):
        ret = OrderedDict((
            ('fullname', obj.fullname),
            ('given_name', obj.given_name),
            ('middle_name', obj.middle_names),
            ('family_name', obj.family_name),
            ('suffix', obj.suffix),
            ('date_registered', obj.date_registered),
            ('gravatar_url', obj.gravatar_url),
            ('employment_institutions', obj.jobs),
            ('educational_institutions', obj.schools),
            ('social_accounts', obj.social)))
        return ret

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        # TODO
        pass


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
