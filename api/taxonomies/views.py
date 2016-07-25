from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ODMFilterMixin
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.taxonomies.serializers import TaxonomySerializer
from api.base.views import JSONAPIBaseView

from modularodm import fields
from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)
from website.project.licenses import NodeLicense

import json


class TaxonomyObject(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    id = fields.StringField(required=True, unique=True, editable=False)
    data = fields.StringField(list=True)

class Taxonomy(JSONAPIBaseView, generics.RetrieveAPIView):

    permission_classes = (

    )

    # required_read_scopes = [CoreScopes.LICENSE_READ]
    # required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer
    view_category = 'taxonomies'
    view_name = 'taxonomy'

    def get_object(self):

        data = json.load('{"data": ["Hello world"]}')
        # self.check_object_permissions(self.request, license)
        return data
