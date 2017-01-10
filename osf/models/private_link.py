from django.utils import timezone
from django.db import models

from framework.utils import iso8601format
from osf.utils.fields import NonNaiveDatetimeField
from website.util import sanitize

from osf.models.base import BaseModel, ObjectIDMixin


class PrivateLink(ObjectIDMixin, BaseModel):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.project.model.PrivateLink'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    date_created = NonNaiveDatetimeField(default=timezone.now)
    key = models.CharField(max_length=512, null=False, unique=True, blank=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    anonymous = models.BooleanField(default=False)

    nodes = models.ManyToManyField('AbstractNode', related_name='private_links')
    creator = models.ForeignKey('OSFUser', null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def node_ids(self):
        return self.nodes.filter(is_deleted=False).values_list('guids___id', flat=True)

    def node_scale(self, node):
        # node may be None if previous node's parent is deleted
        if node is None or node.parent_id not in self.node_ids:
            return -40
        else:
            offset = 20 if node.parent_node is not None else 0
            return offset + self.node_scale(node.parent_node)

    def to_json(self):
        return {
            'id': self._id,
            'date_created': iso8601format(self.date_created),
            'key': self.key,
            'name': sanitize.unescape_entities(self.name),
            'creator': {'fullname': self.creator.fullname, 'url': self.creator.profile_url},
            'nodes': [{'title': x.title, 'url': x.url,
                       'scale': str(self.node_scale(x)) + 'px', 'category': x.category}
                      for x in self.nodes.filter(is_deleted=False)],
            'anonymous': self.anonymous
        }

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        modm_obj.name = modm_obj.name[:255]
        return super(PrivateLink, cls).migrate_from_modm(modm_obj)
