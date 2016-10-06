from django.db import models

from .base import BaseModel, ObjectIDMixin

class NodeRelation(ObjectIDMixin, BaseModel):

    parent = models.ForeignKey('AbstractNode', related_name='node_relations')
    child = models.ForeignKey('AbstractNode')
    is_node_link = models.BooleanField(default=False, db_index=True)

    class Meta:
        order_with_respect_to = 'parent'
        unique_together = ('parent', 'child')
