# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from tests.factories import ProjectFactory

from framework.auth import User, Auth

from website.project import Node
from website.util import api_url_for, web_url_for
from website.addons.app.model import Metadata, AppNodeSettings


class TestMetadataViews(OsfTestCase):

    def setUp(self):
        super(TestMetadataViews, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('app', self.auth)
        self.app_addon = self.project.get_addon('app')

        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_post_metadata(self):
        num = Metadata.find().count()
        url = self.project.api_url_for('create_metadata')
        ret = self.app.post_json(url, {'foo':'bar'})
        assert_equals(ret.status_code, 201)
        assert_true(ret.json['id'])
        assert_equals(Metadata.find().count(), num + 1)

    def test_get_metadata(self):
        meta = Metadata(app=self.app_addon)
        meta.save()

        url = self.project.api_url_for('get_metadata', mid=meta._id)
        ret = self.app.get(url)
        assert_equals(ret.status_code, 200)
        assert_equals(ret.json, {u'_id': meta._id})

    def test_get_metadata_404(self):
        url = self.project.api_url_for('get_metadata', mid='nickelback')
        ret = self.app.get(url, expect_errors=True)
        assert_equals(ret.status_code, 404)

    def test_post_metadata_no_json(self):
        num = Metadata.find().count()
        url = self.project.api_url_for('create_metadata')
        ret = self.app.post_json(url, expect_errors=True)

        assert_equals(ret.status_code, 400)
        assert_equals(Metadata.find().count(), num)

    def test_update_metadata(self):
        meta = Metadata(app=self.app_addon)
        meta['best'] = 'savinme'
        meta.save()

        num = Metadata.find().count()

        url = self.project.api_url_for('update_metadata', mid=meta._id)
        ret = self.app.put_json(url, {'band': 'nickelback'})

        assert_equals(ret.status_code, 200)

        meta.reload()
        assert_equals(meta.to_json(), {
            u'_id': meta._id,
            u'best': 'savinme',
            u'band': 'nickelback'
        })

        assert_equals(Metadata.find().count(), num)

    def test_update_metadata_no_json(self):
        meta = Metadata(app=self.app_addon)
        meta['best'] = 'savinme'
        meta.save()

        num = Metadata.find().count()

        url = self.project.api_url_for('update_metadata', mid=meta._id)
        ret = self.app.put_json(url, expect_errors=True)

        assert_equals(ret.status_code, 400)
        assert_equals(Metadata.find().count(), num)

    def test_update_metadata_no_meta(self):
        num = Metadata.find().count()

        url = self.project.api_url_for('update_metadata', mid='rockstar')
        ret = self.app.put_json(url, {'needsmore': 'nickelback'}, expect_errors=True)

        assert_equals(ret.status_code, 404)
        assert_equals(Metadata.find().count(), num)

    def test_delete_metadata(self):
        meta = Metadata(app=self.app_addon)
        meta['best'] = 'savinme'
        meta.save()

        num = Metadata.find().count()

        url = self.project.api_url_for('delete_metadata', mid=meta._id)
        ret = self.app.delete(url)

        assert_equals(ret.status_code, 204)
        assert_equals(Metadata.load(meta._id), None)
        assert_equals(Metadata.find().count(), num - 1)

    def test_delete_metadata(self):
        meta = Metadata(app=self.app_addon)
        meta['best'] = 'creed'
        meta.save()

        num = Metadata.find().count()

        url = self.project.api_url_for('delete_metadata', mid=meta._id)
        url += '?key=best'
        ret = self.app.delete(url)

        meta.reload()

        assert_equals(ret.status_code, 200)
        assert_equals(ret.json['deleted'], 'best')
        assert_equals(Metadata.find().count(), num)
        assert_equals(meta.get('best'), None)

    def test_delete_metadata_no_meta(self):
        num = Metadata.find().count()

        url = self.project.api_url_for('delete_metadata', mid='cakeordeath')
        ret = self.app.delete(url, expect_errors=True)

        assert_equals(ret.status_code, 404)
        assert_equals(Metadata.find().count(), num)

    def test_promote_metadata_no_meta(self):
        num = Metadata.find().count()
        nodes = Node.find().count()

        url = self.project.api_url_for('promote_metadata', mid='cakeordeath')
        ret = self.app.post(url, expect_errors=True)

        assert_equals(ret.status_code, 404)
        assert_equals(Metadata.find().count(), num)
        assert_equals(Node.find().count(), nodes)

    # TODO Write more tests
    def test_promote_metadata_no_data(self):
        meta = Metadata(app=self.app_addon)
        meta.save()

        num = Metadata.find().count()
        nodes = Node.find().count()

        url = self.project.api_url_for('promote_metadata', mid=meta._id)
        ret = self.app.post(url)

        assert_equals(ret.status_code, 201)
        assert_true(Node.load(ret.json['id']))
        assert_equals(Metadata.find().count(), num)
        assert_equals(Node.find().count(), nodes + 1)

    def test_list_metadatums(self):
        datums = [
            Metadata(app=self.app_addon),
            Metadata(app=self.app_addon),
            Metadata(app=self.app_addon),
            Metadata(app=self.app_addon),
        ]

        [x.save() for x in datums]

        url = self.project.api_url_for('get_metadata_ids')
        ret = self.app.get(url)

        assert_equals(ret.status_code, 200)
        for x in datums:
            assert_in(x._id, ret.json['ids'])

    def test_cant_get_others_data(self):
        other = ProjectFactory()
        other.add_addon('app', self.auth)
        other_app = other.get_addon('app')

        meta = Metadata(app=other_app)
        meta.save()

        url = self.project.api_url_for('get_metadata', mid=meta._id)
        ret = self.app.get(url, expect_errors=True)

        assert_equals(ret.status_code, 403)

    def test_cant_update_others_data(self):
        other = ProjectFactory()
        other.add_addon('app', self.auth)
        other_app = other.get_addon('app')

        meta = Metadata(app=other_app)
        meta.save()

        url = self.project.api_url_for('update_metadata', mid=meta._id)
        ret = self.app.put_json(url, {'isCool': 'nickelback'}, expect_errors=True)

        assert_equals(ret.status_code, 403)

class TestCustomRouteViews(OsfTestCase):

    def setUp(self):
        super(TestCustomRouteViews, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('app', self.auth)
        self.app_addon = self.project.get_addon('app')

        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_create_route(self):
        url = self.project.api_url_for('create_route')
        ret = self.app.post_json(url, {'route': 'nickel', 'query': 'back'})

        self.app_addon.reload()

        assert_equals(ret.status_code, 201)
        assert_true(self.app_addon.routes.get('nickel'))

    def test_create_route_already_made(self):
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('create_route')
        ret = self.app.post_json(url, {'route': 'nickel', 'query': 'back'}, expect_errors=True)


        assert_equals(ret.status_code, 400)

    def test_create_route_no_data(self):
        url = self.project.api_url_for('create_route')
        ret = self.app.post_json(url, {}, expect_errors=True)


        assert_equals(ret.status_code, 400)

    def test_update_route(self):
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('update_route', route='nickel')
        ret = self.app.put_json(url, {'query': 'front'})

        self.app_addon.reload()

        assert_equals(ret.status_code, 200)
        assert_equals(self.app_addon.routes['nickel'], 'front')

    def test_update_route_no_query(self):
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('update_route', route='nickel')
        ret = self.app.put_json(url, {'query': None}, expect_errors=True)

        self.app_addon.reload()

        assert_equals(ret.status_code, 400)

    def test_update_route_no_data(self):
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('update_route', route='nickel')
        ret = self.app.put_json(url, {}, expect_errors=True)

        assert_equals(ret.status_code, 400)

    def test_update_route_no_route(self):
        url = self.project.api_url_for('update_route', route='nickel')
        ret = self.app.put_json(url, {'query': 'front'}, expect_errors=True)

        assert_equals(ret.status_code, 404)

    def test_delete_route(self):
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('update_route', route='nickel')
        ret = self.app.delete(url)

        self.app_addon.reload()

        assert_equals(ret.status_code, 204)
        assert_equals(self.app_addon.routes.get('nickel'), None)

    def test_delete_route_no_route(self):
        url = self.project.api_url_for('update_route', route='nickel')
        ret = self.app.delete(url, expect_errors=True)

        self.app_addon.reload()

        assert_equals(ret.status_code, 400)

    def test_list_routes(self):
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('list_custom_routes')
        ret = self.app.get(url)

        assert_equals(ret.status_code, 200)
        assert_equals(['back'], ret.json.keys())
        assert_in('nickel', ret.json['back'])

    @mock.patch('website.addons.app.views.crud.customroutes.search')
    @mock.patch('website.addons.app.views.crud.customroutes.args_to_query')
    def test_resolve_route(self, mock_query, mock_elastic):
        mock_elastic.return_value = {
            'results': []
        }
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('resolve_route', route='nickel')
        ret = self.app.get(url)

        assert_true(mock_elastic.called)
        assert_equals(ret.status_code, 200)
        mock_query.assert_called_once_with('back', None, None)

    @mock.patch('website.addons.app.views.crud.customroutes.search')
    @mock.patch('website.addons.app.views.crud.customroutes.args_to_query')
    @mock.patch('website.addons.app.views.crud.customroutes.elastic_to_rss')
    def test_resolve_route(self, mock_rss, mock_query, mock_elastic):
        mock_rss.return_value = ''
        mock_elastic.return_value = {
            'results': []
        }
        self.app_addon.routes['nickel'] = 'back'
        self.app_addon.save()
        self.app_addon.reload()

        url = self.project.api_url_for('resolve_route_rss', route='nickel', _xml=True)
        ret = self.app.get(url)

        assert_true(mock_rss.called)
        assert_true(mock_elastic.called)
        assert_equals(ret.status_code, 200)
        mock_query.assert_called_once_with('back', None, None)


class TestAppQueryViews(OsfTestCase):

    def setUp(self):
        super(TestAppQueryViews, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('app', self.auth)
        self.app_addon = self.project.get_addon('app')

        # Log user in
        self.app.authenticate(*self.user.auth)

    @mock.patch('website.addons.app.views.crud.search')
    @mock.patch('website.addons.app.views.crud.args_to_query')
    def test_query_get(self, mock_query, mock_search):
        mock_search.return_value = {}
        url = self.project.api_url_for('query_app')
        ret = self.app.get(url)

        assert_true(mock_search.called)
        assert_equals(ret.status_code, 200)
        mock_query.assert_called_once_with('*', None, None)

    @mock.patch('website.addons.app.views.crud.search')
    @mock.patch('website.addons.app.views.crud.args_to_query')
    def test_query_get_start_finish(self, mock_query, mock_search):
        mock_search.return_value = {}
        url = self.project.api_url_for('query_app')
        ret = self.app.get(url + '?size=10&from=50')

        assert_true(mock_search.called)
        assert_equals(ret.status_code, 200)
        mock_query.assert_called_once_with('*', '10', '50')

    @mock.patch('website.addons.app.views.crud.search')
    @mock.patch('website.addons.app.views.crud.args_to_query')
    def test_query_get_query(self, mock_query, mock_search):
        mock_search.return_value = {}
        url = self.project.api_url_for('query_app')
        ret = self.app.get(url + '?q=horses')

        assert_true(mock_search.called)
        assert_equals(ret.status_code, 200)
        mock_query.assert_called_once_with('horses', None, None)

    @mock.patch('website.addons.app.views.crud.search')
    def test_query_post(self, mock_search):
        mock_search.return_value = {}
        url = self.project.api_url_for('query_app_json')
        ret = self.app.get(url)

        assert_true(mock_search.called)
        assert_equals(ret.status_code, 200)

    @mock.patch('website.addons.app.views.crud.search')
    def test_query_post_no_json(self, mock_search):
        mock_search.return_value = {}
        url = self.project.api_url_for('query_app_json')
        ret = self.app.post(url, expect_errors=True)

        assert_equals(ret.status_code, 400)
        assert_false(mock_search.called)

    @mock.patch('website.addons.app.views.crud.search')
    def test_query_post_empty_json(self, mock_search):
        mock_search.return_value = {}
        url = self.project.api_url_for('query_app_json')
        ret = self.app.post_json(url, {}, expect_errors=True)

        assert_equals(ret.status_code, 400)
        assert_false(mock_search.called)
