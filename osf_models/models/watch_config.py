from django.db import models

from osf_models.models.base import BaseModel, ObjectIDMixin

class WatchConfig(ObjectIDMixin, BaseModel):
    node = models.ForeignKey('AbstractNode', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey('OSFUser', on_delete=models.SET_NULL, null=True, blank=True)

    digest = models.BooleanField(default=False)
    immediate = models.BooleanField(default=False)

    def __repr__(self):
        return '<WatchConfig(node="{self.node}")>'.format(self=self)

    class Meta:
        unique_together = ('user', 'node')
