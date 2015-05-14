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

    # TODO: Implement validators, eg https://docs.djangoproject.com/en/1.8/ref/validators/#urlvalidator

    id = ser.CharField(read_only=True, source='_id')

    client_id = ser.CharField(read_only=True)
    client_secret = ser.CharField(read_only=True)  # TODO: May change this later

    owner = ser.CharField(required=True, source='owner._id', validators=[user_validator])

    name = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True)

    reg_date = ser.DateTimeField(read_only=True)

    home_url = ser.CharField(required=True, validators=[URLValidator()])
    callback_url = ser.CharField(required=True, validators=[URLValidator()])

    def to_internal_value(self, data):
        """
        Total hack to make update/patch operations work: if data is nested under a key "data", this extracts it

        It will break schemas that happen to include a field named "data".
        :param data:
        :return:
        """
        # FIXME: Fix this the right way without a hack. Why is request.data nested for update/patch but not create?
        if "data" in data:
            data = data["data"]
        return super(OAuth2AppSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        # TODO: Known issue- create view allows creating duplicate entries.
        # If the data passed contains read_only fields, the model will be created with auto-populated different values of those fields.
        # This won't result in a key collision, but it's pretty confusing to an external user. Should fail if request contains those keys?
        instance = OAuth2App(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        assert isinstance(instance, OAuth2App), 'instance must be an OAuth2App'

        # TODO: This silently fails to populated validated_data because to_internal_value can't deal with nesting:
        ## Request.data reads {u'data': {u'callback_url': u'www.cos.io', u'description': u'BB', u'reg_date': u'2015-05-14T19:04:54.784313', u'client_id': u'3d99eb57a1ff4751bedd24a09655f9ff', u'owner': u'4urxt', u'client_secret': u'ZGFhY2ViMDliOGI1NDUwZDg3NjU2OGVjNmIwZDNkMGE=', u'home_url': u'www.google.com', u'type': u'applications', u'id': u'5554f1d69f8b1f98ec7825b0', u'name': u'AAeee'}}
        #   instead of the data being at the top level. Creates work because they send the right data; patch fails because it nests

        for attr, value in validated_data.iteritems():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        type_ = 'applications'
