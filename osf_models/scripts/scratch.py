from __future__ import print_function
from __future__ import unicode_literals

import inspect
from pprint import pprint
from django.apps import apps
from osf_models import models

# https://github.com/django/django/blob/master/django/db/migrations/topological_sort.py
# https://github.com/django/django/blob/master/django/db/migrations/graph.py#L310

def get_model_topology():
    classes = set([tup[1] for tup in inspect.getmembers(models) if isinstance(tup[1], type)])
    all_models = set(apps.get_models())
    app_models = classes.intersection(all_models)

    relationship_map = {}
    topology = list()
    for model in app_models:
        relationship_map[model] = set([getattr(field, 'through', field.related_model)
                               for field_name, field in
                               model._meta._forward_fields_map.iteritems()
                               if field.related_model is not model and
                               field.related_model is not None])

    while relationship_map:
        for model, relationships in tuple(relationship_map.iteritems()):
            print(model, relationships)
            relationships.discard(model)
            relationship_map[model] = relationships - set(topology)
            if len(relationships) < 1:
                print('deleted {}'.format(model))
                topology.append(model)
                del relationship_map[model]

    pprint(topology)
