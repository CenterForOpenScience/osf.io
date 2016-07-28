from rest_framework import generics

from website.project.taxonomies import Subject

from api.taxonomies.serializers import TaxonomySerializer
from api.base.views import JSONAPIBaseView

import json


class PlosTaxonomyMixin(JSONAPIBaseView, generics.RetrieveAPIView):
    serializer_class = TaxonomySerializer
    view_category = 'plos-taxonomies'

    # overrides RetrieveAPIView
    def get_object(self):
        with open(self.data_file, 'r') as json_file:
            data = json.load(json_file)
        return data

class PlosTaxonomyFlat(PlosTaxonomyMixin):
    '''[PLOS taxonomy of subjects](http://journals.plos.org/plosone/browse/) in flattened form. *Read-only*

    ##Taxonomy Attributes

        name           type                   description
        ----------------------------------------------------------------------------
        data           array of strings       List of subjects

    Each subject is formatted as an underscore-separated string,
    where a string with no underscores indicates the subject is at the highest level
    of the taxonomy and all subsequent underscores indicate subjects further down
    the taxonomy. For example,

        "Biology and life sciences_Agriculture_Agricultural biotechnology"

    indicates that "Biology and life sciences" is the parent subject of "Agriculture"
    which is the parent subject of "Agricultural biotechnology".

    Including `reverse=true` as a query parameter (`v2/taxonomies/plos/flat?reverse=true`) will return the same list
    but with each subject underscore-separated in reverse order (lowest subject first).

    Only the top three levels of the PLOS taxonomy are included.
    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly
    )

    view_name = 'plos-taxonomy-flat'

    @property
    def data_file(self):
        # Handle reverse=true query parameter
        reverse_flag = self.request.query_params.get('reverse')
        if (reverse_flag and reverse_flag.lower() == 'true' or reverse_flag == '1'):
            return 'api/static/json/top_3_levels_flat_reverse.json'
        return 'api/static/json/top_3_levels_flat.json'



class PlosTaxonomyTreeview(PlosTaxonomyMixin):
    '''[PLOS taxonomy of subjects](http://journals.plos.org/plosone/browse/) in the format expected by
    [bootstrap-treeview](https://github.com/jonmiles/bootstrap-treeview).
    *Read-only*

    ##Taxonomy Attributes

        name           type                      description
        ---------------------------------------------------------------------------------------------------
        data           array of JSON objects     List of subjects as objects with 'text' and 'nodes' fields

    Bootstrap-treeview is a tool for displaying tree structures in a clean, Bootstrap-styled list. The PLOS
    taxonomy has been parsed to fit the format bootstrap-treeview expects, which entails each subject being
    represented by an object with two key fields: `text` and `nodes`. In this case, `text` is a single-element
    array that contains the subject itself as a string. `nodes` is an array of child objects each with their own
    `text` and `nodes` fields, with the exception that leaf nodes do not contain a `nodes` field.
    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly
    )

    view_name = 'plos-taxonomy-treeview'
    data_file = 'api/static/json/top_3_levels_treeview.json'
