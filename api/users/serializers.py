from rest_framework import serializers as ser
from django.core.validators import URLValidator


from api.base.serializers import JSONAPISerializer, LinksField, Link

from website.models import OAuth2App, User


def user_validator(user):
    """
    Raise a validation error if this is not a user object (or a valid user ID)
    """
    if isinstance(user, User):
        return True
    elif isinstance(user, basestring):
        try:
            User.load(user)
        except:
            raise ser.ValidationError("Must specify a valid user ID")
    else:
        raise ser.ValidationError("Must provide valid user object or ID string")


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
    given_name = ser.CharField(help_text='For bibliographic citations')
    middle_name = ser.CharField(source='middle_names', help_text='For bibliographic citations')
    family_name = ser.CharField(help_text='For bibliographic citations')
    suffix = ser.CharField(help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.CharField(help_text='URL for the icon used to identify the user. Relies on http://gravatar.com ')
    employment_institutions = ser.ListField(source='jobs', help_text='An array of dictionaries representing the '
                                                                     'places the user has worked')
    educational_institutions = ser.ListField(source='schools', help_text='An array of dictionaries representing the '
                                                                         'places the user has attended school')
    social_accounts = ser.DictField(source='social', help_text='A dictionary of various social media account '
                                                               'identifiers including an array of user-defined URLs')

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
        # TODO
        pass


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')

    def get_bibliographic(self, obj):
        node = self.context['view'].get_node()
        return obj._id in node.visible_contributor_ids


class OAuth2AppSerializer(JSONAPISerializer):
    """Serialize data about a registered OAuth2 application"""

    #id = ser.CharField(read_only=True, source='_id')

    client_id = ser.CharField(help_text="The client ID for this application (automatically generated)",
                              read_only=True)
    client_secret = ser.CharField(help_text="The client secret for this application (automatically generated)",
                                  read_only=True)  # TODO: May change this later

    owner = ser.CharField(help_text="The id of the user who owns this application",
                          read_only=True,  # TODO: The serializer does not control creating/changing this field directly
                          source='owner._id',

                          validators=[user_validator])  # TODO: Make readonly??

    name = ser.CharField(help_text="A short, descriptive name for this application",
                         required=True)
    description = ser.CharField(help_text="An optional description displayed to all users of this application",
                                required=False,
                                allow_blank=True)

    reg_date = ser.DateTimeField(help_text="The date this application was generated (automatically filled in)",
                                 read_only=True)

    home_url = ser.CharField(help_text="The full URL to this application's homepage.",
                             required=True,
                             validators=[URLValidator()])
    callback_url = ser.CharField(help_text="The callback URL for this application (refer to OAuth documentation)",
                                 required=True,
                                 validators=[URLValidator()])

    def create(self, validated_data):
        # TODO: Known issue- create view allows creating duplicate entries.
        # If the data passed contains read_only fields, the model will be created with auto-populated different values of those fields.
        # This won't result in a key collision, but it's pretty confusing to an external user. Should fail if request contains those keys?
        instance = OAuth2App(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        assert isinstance(instance, OAuth2App), 'instance must be an OAuth2App'
        for attr, value in validated_data.iteritems():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        type_ = 'applications'
