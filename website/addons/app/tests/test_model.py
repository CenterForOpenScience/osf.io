# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import AuthFactory
from tests.factories import ProjectFactory

from framework.auth import User

from website.addons.app.model import Metadata, AppNodeSettings
from website.search.exceptions import TypeCollisionError

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

        assert_equals(meta.to_json(), data)

    def test_merge_nested_dict(self):
        meta = Metadata(app=self.app)
        meta['foo'] = {'bar': 'zyzz', 'zyzz': 10}

        meta.update({
            'foo': {
                'baz': 4,
                'zyzz': 11
            }
        })

        data = {'foo': {'bar': 'zyzz', 'baz': 4, 'zyzz': 11}}
        data['_id'] = meta._id

        assert_equals(meta.to_json(), data)

    def test_merge_nested_list(self):
        meta = Metadata(app=self.app)
        meta['foo'] = [1,2,3]

        meta.update({
            'foo': [4,5,6]
        })

        data = {'foo': [1,2,3,4,5,6]}
        data['_id'] = meta._id

        assert_equals(meta.to_json(), data)

    def test_implicit_keys(self):
        meta = Metadata(app=self.app)

        meta.save()
        meta.reload()

        assert_equals(meta.to_json()['_id'], meta._id)

    def test_attached_node(self):
        meta = Metadata(app=self.app)
        meta['attached'] = {
            'nid': self.project._id
        }

        meta.save()
        meta.reload()

        assert_equals(meta.node, self.project)

    def test_attached_none(self):
        meta = Metadata(app=self.app)

        meta.save()
        meta.reload()

        assert_equals(meta.node, None)
        assert_equals(meta.parent, None)
        assert_equals(meta.children, [])
        assert_equals(meta.project, None)

    def test_conflicting_types(self):
        meta = Metadata(app=self.app)
        meta.update({'bar': 'zyzz', 'zyzz': 10})

        meta.save()
        meta.reload()

        meta.update({
            'baz': 49,
            'zyzz': 'str'
        })

        self.assertRaises(TypeCollisionError, meta.save)

    def test_conflicting_types_str_dict(self):
        meta = Metadata(app=self.app)
        meta.update({'bax': 'zyzz'})

        meta.save()
        meta.reload()

        meta.update({
            'bax': {}
        })

        meta.save()
        meta.reload()

        assert_equal(meta.data, {'bax': {}})

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

    def test_duck_dictionary(self):
        meta = Metadata(app=self.app)

        meta['ducks'] = 'cool'
        assert_equals(meta['ducks'], 'cool')

        del meta['ducks']
        assert_equals(meta.get('ducks'), None)


class TestAppSettings(OsfTestCase):

    def setUp(self):
        super(TestAppSettings, self).setUp()
        self.auth = AuthFactory()
        self.project = ProjectFactory()

    def test_can_add_addon(self):
        self.project.add_addon('app', self.auth)
        assert_not_equal(self.project.get_addon('app'), None)

    def test_user_created(self):
        num = User.find().count()
        self.project.add_addon('app', self.auth)
        assert_equals(num + 1, User.find().count())

        app = self.project.get_addon('app')
        assert_not_equal(app.system_user, None)

    def test_user_password(self):
        self.project.add_addon('app', self.auth)
        app = self.project.get_addon('app')
        assert_equals(app.system_user.password, '12')

    def test_namespace_is_id(self):
        self.project.add_addon('app', self.auth)
        app = self.project.get_addon('app')
        assert_equals(app.namespace, self.project._id)

    def test_name_is_title(self):
        self.project.add_addon('app', self.auth)
        app = self.project.get_addon('app')
        assert_equals(app.name, self.project.title)

    def test_all_data(self):
        self.project.add_addon('app', self.auth)
        app = self.project.get_addon('app')
        metadatas = [
            Metadata(app=app),
            Metadata(app=app),
            Metadata(app=app)
        ]
        [x.save() for x in metadatas]
        app.reload()

        metadatums = app.all_data

        assert_equals(len(metadatums), 3)

        for m in metadatas:
            assert_in(m, metadatums)
