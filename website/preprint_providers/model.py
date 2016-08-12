from django.core.urlresolvers import reverse

from modularodm import Q
from modularodm.query.query import RawQuery
from modularodm.storage.mongostorage import MongoQuerySet

from website.institutions.model import Institution, InstitutionQuerySet


class ProviderQuerySet(InstitutionQuerySet):

    def __iter__(self):
        for each in super(ProviderQuerySet, self).__iter__():
            yield PreprintProvider(each)

    def _do_getitem(self, index):
        item = super(ProviderQuerySet, self)._do_getitem(index)
        if isinstance(item, MongoQuerySet):
            return self.__class__(item)
        return PreprintProvider(item)


class PreprintProvider(Institution):
    attribute_map = {
        '_id': 'institution_id',
        'name': 'title',
        'domains': 'institution_domains',
        'logo_name': 'institution_logo_name',
        'description': 'description',
        'banner_name': 'institution_banner_name',
        'is_deleted': 'is_deleted',
    }

    def save(self):
        for key, value in self.attribute_map.iteritems():
            if getattr(self, key) != getattr(self.node, value):
                setattr(self.node, value, getattr(self, key))
        self.node.save()

    @classmethod
    def find(cls, query=None, deleted=False, **kwargs):
        from website.models import Node  # done to prevent import error
        if query and getattr(query, 'nodes', False):
            for node in query.nodes:
                replacement_attr = cls.attribute_map.get(node.attribute, False)
                node.attribute = replacement_attr or node.attribute
        elif isinstance(query, RawQuery):
            replacement_attr = cls.attribute_map.get(query.attribute, False)
            query.attribute = replacement_attr or query.attribute
        query = query & Q('institution_id', 'ne', None) if query else Q('institution_id', 'ne', None)
        query = query & Q('is_deleted', 'ne', True) if not deleted else query
        nodes = Node.find(query, allow_institution=True, **kwargs)
        return ProviderQuerySet(nodes)

    @property
    def api_v2_url(self):
        return reverse('preprint_providers:provider-detail', kwargs={'institution_id': self._id})

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('preprint_providers:provider-detail', kwargs={'institution_id': self._id})

    @property
    def nodes_url(self):
        return self.absolute_api_v2_url + 'preprints/'

    @property
    def nodes_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/preprints/'

    @property
    def logo_path(self):
        if self.logo_name:
            return '/static/img/preprint_providers/{}'.format(self.logo_name)
        else:
            return None

    @property
    def banner_path(self):
        if self.banner_name:
            return '/static/img/preprint_providers/{}'.format(self.banner_name)
        else:
            return None
