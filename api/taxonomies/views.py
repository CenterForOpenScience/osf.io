from rest_framework import generics

from api.taxonomies.serializers import TaxonomySerializer
from api.base.views import JSONAPIBaseView

from modularodm import fields
from framework.mongo import (
    ObjectId,
    StoredObject,
)

import json

class TaxonomyMixin(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
    )
    serializer_class = TaxonomySerializer
    view_category = 'taxonomies'
    view_name = 'taxonomy'
    data_file = ''

    def get_object(self):
        with open(self.data_file, 'r') as json_file:
            data = json.load(json_file)
        return data

class TaxonomyObject(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    id = fields.StringField(required=True, unique=True, editable=False)
    data = fields.StringField(list=True)

class TaxonomyFlat(TaxonomyMixin):
    data_file = 'api/static/json/top_3_levels_flat.json'
    id = 'flat'

class TaxonomyTreeview(TaxonomyMixin):
    data_file = 'api/static/json/top_3_levels_treeview.json'
    id = 'treeview'
