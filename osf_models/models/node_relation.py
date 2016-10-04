from django.db import models

from .base import BaseModel, ObjectIDMixin

class NodeRelation(ObjectIDMixin, BaseModel):

    source = models.ForeignKey('AbstractNode', related_name='node_relations')
    dest = models.ForeignKey('AbstractNode')
    is_node_link = models.BooleanField(default=False, db_index=True)

    class Meta:
        order_with_respect_to = 'source'
        unique_together = ('source', 'dest')
