from rest_framework import serializers as ser
from django.core.validators import URLValidator

from api.base.serializers import JSONAPISerializer, LinksField, Link

from website.models import ApiOAuth2Application, User
from website.util.sanitize import strip_html

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


class ApiOAuth2ApplicationSerializer(JSONAPISerializer):
    """Serialize data about a registered OAuth2 application"""
    client_id = ser.CharField(help_text="The client ID for this application (automatically generated)",
                              read_only=True)

    client_secret = ser.CharField(help_text="The client secret for this application (automatically generated)",
                                  read_only=True)  # TODO: May change this later

    owner = ser.CharField(help_text="The id of the user who owns this application",
                          read_only=True,  # Don't let user register an application in someone else's name
                          source='owner._id',
                          validators=[user_validator])

    name = ser.CharField(help_text="A short, descriptive name for this application",
                         required=True)

    description = ser.CharField(help_text="An optional description displayed to all users of this application",
                                required=False,
                                allow_blank=True)

    create_date = ser.DateTimeField(help_text="The date this application was generated (automatically filled in)",
                                    read_only=True)

    home_url = ser.CharField(help_text="The full URL to this application's homepage.",
                             required=True,
                             validators=[URLValidator()])

    callback_url = ser.CharField(help_text="The callback URL for this application (refer to OAuth documentation)",
                                 required=True,
                                 validators=[URLValidator()])

    class Meta:
        type_ = 'applications'

    links = LinksField({
        'html': 'absolute_url'
    })

    def absolute_url(self, obj):
        return obj.absolute_url

    def is_valid(self, *args, **kwargs):
        """After validation, scrub HTML from validated_data prior to saving (for create and update views)"""
        ret = super(ApiOAuth2ApplicationSerializer, self).is_valid(*args, **kwargs)
        for k, v in self.validated_data.iteritems():
            self.validated_data[k] = strip_html(v)
        return ret

    def create(self, validated_data):
        instance = ApiOAuth2Application(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        assert isinstance(instance, ApiOAuth2Application), 'instance must be an ApiOAuth2Application'
        for attr, value in validated_data.iteritems():
            setattr(instance, attr, value)
        instance.save()
        return instance
