# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import AuthFactory
from tests.factories import ProjectFactory

from website.addons.app.model import Metadata, AppNodeSettings


class TestMetadata(OsfTestCase):

    def setUp(self):
        super(TestMetadata, self).setUp()
        self.auth = AuthFactory()
        self.project = ProjectFactory()

        self.project.add_addon('app', self.auth)
        self.app = self.project.get_addon('app')

    def test_namespace(self):
        meta = Metadata(app=self.app)
        assert_equals(self.app.namespace, meta.namespace)

    def test_storing(self):
        meta = Metadata(app=self.app)
        meta['test'] = 'foo'
        meta['bar'] = {'baz': 'zyzz'}

        meta.save()
        meta.reload()

        data = {'test':'foo', 'bar':{'baz':'zyzz'}}
        data['_id'] = meta._id
        data['category'] = 'metadata'

        assert_equals(meta.data, data)

    def test_implicit_keys(self):
        meta = Metadata(app=self.app)

        meta.save()
        meta.reload()

        assert_equals(meta['_id'], meta._id)
        assert_equals(meta['category'], 'metadata')

    def test_attached_node(self):
        meta = Metadata(app=self.app)
        meta['attached'] = {
            'nid': self.project._id
        }

        meta.save()
        meta.reload()

        assert_equals(meta.node, self.project)

    def test_attached_project(self):
        meta = Metadata(app=self.app)
        meta['attached'] = {
            'pid': self.project._id
        }

        meta.save()
        meta.reload()

        assert_equals(meta.project, self.project)

    def test_attached_parent(self):
        meta1 = Metadata(app=self.app)
        meta2 = Metadata(app=self.app)

        meta2.save()
        meta2.reload()

        meta1['attached'] = {
            'pmid': meta2._id
        }
        meta1.save()
        meta1.reload()

        assert_equals(meta1.parent, meta2)

    def test_attached_children(self):
        meta1 = Metadata(app=self.app)
        meta2 = Metadata(app=self.app)
        meta3 = Metadata(app=self.app)

        meta2.save()
        meta2.reload()

        meta3.save()
        meta3.reload()

        meta1['attached'] = {
            'cmids': [meta2._id, meta3._id]
        }

        meta1.save()
        meta1.reload()

        assert_in(meta2, meta1.children)
        assert_in(meta3, meta1.children)
