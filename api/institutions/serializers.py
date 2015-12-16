import json
import uuid

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from rest_framework import serializers as ser
from rest_framework.exceptions import NotFound

from website import security
from website.models import Institution, User
from framework.auth import signals
from framework.auth.core import get_user
from api.base.serializers import JSONAPISerializer, RelationshipField, LinksField

def find_institution_by_domain(username):
    domain = username.split('@')[1]
    try:
        inst = Institution.find_one(Q('domains', 'eq', domain))
    except NoResultsFound:
        raise NotFound
    return inst

def get_or_create_user(fullname, address):
    """Copy from conferences code
    """
    user = get_user(email=address)
    if user:
        return user, False
    else:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        user.verification_key = security.random_string(20)
        signals.user_confirmed.send(user)
        return user, True

class InstitutionSerializer(JSONAPISerializer):
    name = ser.CharField(required=False)
    id = ser.CharField(required=False, source='_id')
    logopath = ser.CharField(source='logo_path')
    links = LinksField({'self': 'get_api_url',
                        'html': 'get_absolute_url', })

    nodes = RelationshipField(
        related_view='institutions:institution-nodes',
        related_view_kwargs={'institution_id': '<pk>'},
    )

    users = RelationshipField(
        related_view='institutions:institution-users',
        related_view_kwargs={'institution_id': '<pk>'}
    )

    def get_api_url(self, obj):
        return obj.get_api_url()

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'institutions'


class InstitutionAuthSerializer(ser.Serializer):
    def create(self, *args, **kwargs):
        data = self.context['request'].data
        institution = find_institution_by_domain(data['username'])
        fullname_field = institution.metadata_request_fields.get('fullname')
        fullname = data['data'].get(fullname_field)

        user, user_created = get_or_create_user(fullname=fullname, address=data['username'])

        if institution not in user.affiliated_institutions:
            user.affiliated_institutions.append(institution)

        current_data = user.institutions_metadata.get(institution._id)
        if not current_data:
            user.institutions_metadata[institution._id] = json.dumps(data['data'])
        else:
            current_data = json.loads(current_data)
            current_data.update(data['data'])
            user.institutions_metadata[institution._id] = current_data
        user.save()

        import ipdb; ipdb.set_trace()

