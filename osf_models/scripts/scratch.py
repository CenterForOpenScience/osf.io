from __future__ import unicode_literals

from pprint import pprint

from collections import OrderedDict

from modularodm import Q as MQ
from osf_models.models import (MetaSchema, Guid, BlackListGuid, OSFUser, Contributor, Node, NodeLog, Tag, Embargo, Retraction)

models = [MetaSchema, Guid, BlackListGuid, OSFUser, Contributor, Node, NodeLog, Tag, Embargo, Retraction]


# def get_model_topology(models):
#     relationship_map = {}
#     topology = list()
#     for model in models:
#         relationship_map[model] = set([field.related_model
#                                for field_name, field in
#                                model._meta._forward_fields_map.iteritems()
#                                if field.related_model is not model and
#                                field.related_model is not None])
#
#     for model, relationships in relationship_map.iteritems():
#         filtered_relationships = relationships - set(topology)
#         topology.append(model)
#         relationship_map[model] = filtered_relationships
#
#     pprint(topology)


def get_model_topology(models):
    relationship_map = {}
    topology = list()
    for model in models:
        relationship_map[model] = set([getattr(field, 'through', field.related_model)
                               for field_name, field in
                               model._meta._forward_fields_map.iteritems()
                               if field.related_model is not model and
                               field.related_model is not None])


    while relationship_map:
        for model, relationships in tuple(relationship_map.iteritems()):
            print model, relationships
            relationships.discard(model)
            relationship_map[model] = relationships - set(topology)
            if len(relationships) < 1:
                print 'deleted {}'.format(model)
                topology.append(model)
                del relationship_map[model]

    pprint(topology)
