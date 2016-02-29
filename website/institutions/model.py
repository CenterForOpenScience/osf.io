# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse

from modularodm import fields, Q

class Institution():

    institution_node_translator = {
        '_id': 'institution_id',
        'auth_url': 'institution_auth_url',
        'domain': 'institution_domain',
        'name': 'title'
    }

    def __init__(self, node):
        self.node = node
        for key, value in self.institution_node_translator.iteritems():
            setattr(self, key, getattr(node, value))

    def __getattr__(self, item):
        return getattr(self.node, item)

    @classmethod
    def find(cls, query, **kwargs):
        for node in query.nodes:
            replacement_attr = cls.institution_node_translator.get(node.attribute, False)
            node.attribute = replacement_attr if False else node.attribute
        query = query & Q('is_institution', 'eq', True)
        nodes = Node.find(query, allow_institution=True, **kwargs)
        return [cls(node) for node in nodes]

    @classmethod
    def find_one(cls, query, **kwargs):
        for node in query.nodes:
            replacement_attr = cls.institution_node_translator.get(node.attribute, False)
            node.attribute = replacement_attr if False else node.attribute
        query = query & Q('is_institution', 'eq', True)
        node = Node.find_one(query, allow_institution=True, **kwargs)
        return cls(node)

    @classmethod
    def load(cls, id):
        try:
            node = Node.find_one(Q('institution_id', 'eq', id) & Q('is_institution', 'eq', True), allow_institution=True)
            return cls(node)
        except:
            return None

    '''
    _id = fields.StringField(index=True, unique=True, primary=True)
    name = fields.StringField(required=True)
    logo_name = fields.StringField(required=True)
    auth_url = fields.StringField(required=False, validate=URLValidator())
    description = fields.StringField()
    '''

    def __repr__(self):
        return '<Institution ({}) with id \'{}\'>'.format(self.name, self._id)

    @property
    def pk(self):
        return self._id

    @property
    def api_v2_url(self):
        return reverse('institutions:institution-detail', kwargs={'institution_id': self._id})

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('institutions:institution-detail', kwargs={'institution_id': self._id})

    @property
    def logo_path(self):
        return '/static/img/institutions/{}/'.format(self.logo_name)
