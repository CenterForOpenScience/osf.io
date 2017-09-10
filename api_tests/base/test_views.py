# -*- coding: utf-8 -*-
import httplib as http
import importlib
import mock
import pkgutil
import pytest

from django.contrib.auth.models import User

from api.base.permissions import TokenHasScope
from api.base.settings.defaults import API_BASE
from framework.auth.oauth_scopes import CoreScopes
from osf_tests.factories import AuthUserFactory, ProjectFactory
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from website.settings import DEBUG_MODE
from website import maintenance


URLS_MODULES = []
for loader, name, _ in pkgutil.iter_modules(['api']):
    if name != 'base' and name != 'test':
        try:
            URLS_MODULES.append(importlib.import_module('api.{}.urls'.format(name)))
        except ImportError:
            pass

VIEW_CLASSES = []
for mod in URLS_MODULES:
    urlpatterns = mod.urlpatterns
    for patt in urlpatterns:
        VIEW_CLASSES.append(patt.callback.cls)

@pytest.mark.django_db
class TestApiBaseViews:

    def test_root_returns_200(self, app):
        res = app.get('/{}'.format(API_BASE))
        assert res.status_code == 200

    def test_does_not_exist_returns_404(self, app):
        res = app.get('/{}{}'.format(API_BASE,'notapage'), expect_errors=True)
        assert res.status_code == 404

    def test_does_not_exist_formatting(self, app):
        url = '/{}{}/'.format(API_BASE, 'notapage')
        res = app.get(url, expect_errors=True)
        errors = res.json['errors']
        assert isinstance(errors, list) is True
        assert errors[0] == {'detail': 'Not found.'}

    def test_view_classes_have_minimal_set_of_permissions_classes(self):
        base_permissions = [
            TokenHasScope,
            (IsAuthenticated, IsAuthenticatedOrReadOnly)
        ]
        for view in VIEW_CLASSES:
            for cls in base_permissions:
                if isinstance(cls, tuple):
                    has_cls = any([c in view.permission_classes for c in cls])
                    assert has_cls, "{0} lacks the appropriate permission classes".format(view)
                else:
                    assert cls in view.permission_classes, "{0} lacks the appropriate permission classes".format(view)
            for key in ['read', 'write']:
                scopes = getattr(view, 'required_{}_scopes'.format(key), None)
                assert bool(scopes)
                for scope in scopes:
                    assert scope is not None
                if key == 'write':
                    assert CoreScopes.ALWAYS_PUBLIC not in scopes

    def test_view_classes_support_embeds(self):
        for view in VIEW_CLASSES:
            assert hasattr(view, '_get_embed_partial'), "{0} lacks embed support".format(view)

    def test_view_classes_define_or_override_serializer_class(self):
        for view in VIEW_CLASSES:
            has_serializer_class = getattr(view, 'serializer_class', None) or getattr(view, 'get_serializer_class', None)
            assert has_serializer_class, "{0} should include serializer class or override get_serializer_class()".format(view)

    def test_unconfirmed_user_gets_error(self, app):
        with mock.patch('osf.models.OSFUser.is_confirmed', mock.PropertyMock(return_value=False)):
            user = AuthUserFactory()
            res = app.get('/{}nodes/'.format(API_BASE), auth=user.auth, expect_errors=True)
        assert res.status_code == http.BAD_REQUEST

    def test_disabled_user_gets_error(self, app):
        with mock.patch('osf.models.OSFUser.is_disabled', mock.PropertyMock(return_value=True)):
            user = AuthUserFactory()
            res = app.get('/{}nodes/'.format(API_BASE), auth=user.auth, expect_errors=True)
        assert res.status_code == http.BAD_REQUEST

@pytest.mark.django_db
class TestStatusView:

    def test_status_view(self, app):
        url = '/{}status/'.format(API_BASE)

        #test_status_view_wo_maintenance
        res = app.get(url)
        assert res.status_code == 200
        assert res.json == {'maintenance': None}

        #test_status_view_with_maintenance
        maintenance.set_maintenance(message='test')
        res = app.get(url)
        m = maintenance.get_maintenance()
        assert res.status_code == 200
        assert res.json['maintenance']['level'] == 1
        assert res.json['maintenance']['start'] == m['start']
        assert res.json['maintenance']['end'] == m['end']
        assert res.json['maintenance']['message'] == 'test'


@pytest.mark.django_db
class TestJSONAPIBaseView:

    def test_json_api_base_view(self, app):
        user = AuthUserFactory()
        node = ProjectFactory(creator=user)
        url = '/{0}nodes/{1}/'.format(API_BASE, node._id)
        for i in range(5):
            ProjectFactory(parent=node, creator=user)
        for i in range(5):
            ProjectFactory(parent=node)

        #test_request_added_to_serializer_context
        with mock.patch('api.base.serializers.JSONAPISerializer.to_representation', autospec=True) as  mock_to_representation:
            url = '/{0}nodes/{1}/'.format(API_BASE, node._id)
            app.get(url, auth=user.auth)
            assert 'request' in mock_to_representation.call_args[0][0].context

        #test_reverse_sort_possible
        res = app.get('http://localhost:8000/v2/users/me/nodes/?sort=-title', auth=user.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestSwaggerDocs:

    def test_swagger_docs_redirect_to_root(self, app):
        res = app.get('/v2/docs/')
        assert res.status_code == 302
        assert res.location == '/v2/'
