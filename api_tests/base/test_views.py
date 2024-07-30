from rest_framework import status as http_status
import pkgutil

from unittest import mock

from tests.base import ApiTestCase
from osf_tests import factories
from osf.utils.permissions import READ, WRITE
from framework.auth.oauth_scopes import CoreScopes

from api.base.settings.defaults import API_BASE
from api.search.permissions import IsAuthenticatedOrReadOnlyForSearch
from api.crossref.views import ParseCrossRefConfirmation
from api.metrics.views import (
    RawMetricsView,
    RegistriesModerationMetricsView,
    CountedAuthUsageView,
    MetricsOpenapiView,
)
from api.users.views import ClaimUser
from api.wb.views import MoveFileMetadataView, CopyFileMetadataView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from api.base.permissions import TokenHasScope
from website.settings import DEBUG_MODE
from website import maintenance

import importlib

URLS_MODULES = []
for loader, name, _ in pkgutil.iter_modules(['api']):
    if name != 'base' and name != 'test':
        try:
            URLS_MODULES.append(
                importlib.import_module(f'api.{name}.urls')
            )
        except ImportError:
            pass

VIEW_CLASSES = []
for mod in URLS_MODULES:
    urlpatterns = mod.urlpatterns
    for patt in urlpatterns:
        if hasattr(patt, 'url_patterns'):
            # Namespaced list of patterns
            for subpatt in patt.url_patterns:
                VIEW_CLASSES.append(subpatt.callback.cls)
        else:
            VIEW_CLASSES.append(patt.callback.cls)


class TestApiBaseViews(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.EXCLUDED_VIEWS = [
            ClaimUser,
            CopyFileMetadataView,
            CountedAuthUsageView,
            MoveFileMetadataView,
            ParseCrossRefConfirmation,
            RawMetricsView,
            RegistriesModerationMetricsView,
            MetricsOpenapiView,
        ]

    def test_root_returns_200(self):
        res = self.app.get(f'/{API_BASE}')
        assert res.status_code == 200

    def test_does_not_exist_returns_404(self):
        res = self.app.get(
            '/{}{}'.format(API_BASE, 'notapage'),
            expect_errors=True
        )
        assert res.status_code == 404

    def test_does_not_exist_formatting(self):
        if DEBUG_MODE:
            self.skipTest('Skipped because debug mode')
        else:
            url = '/{}{}/'.format(API_BASE, 'notapage')
            res = self.app.get(url, expect_errors=True)
            errors = res.json['errors']
            assert isinstance(errors, list)
            assert errors[0] == {'detail': 'Not found.'}

    def test_view_classes_have_minimal_set_of_permissions_classes(self):
        base_permissions = [
            TokenHasScope,
            (IsAuthenticated, IsAuthenticatedOrReadOnly, IsAuthenticatedOrReadOnlyForSearch)
        ]
        for view in VIEW_CLASSES:
            if view in self.EXCLUDED_VIEWS:
                continue
            for cls in base_permissions:
                if isinstance(cls, tuple):
                    has_cls = any([c in view.permission_classes for c in cls])
                    assert has_cls, f'{view} lacks the appropriate permission classes'
                else:
                    assert cls in view.permission_classes, f'{view} lacks the appropriate permission classes'
            for key in [READ, WRITE]:
                scopes = getattr(view, f'required_{key}_scopes', None)
                assert bool(scopes)
                for scope in scopes:
                    assert scope is not None
                if key == WRITE:
                    assert CoreScopes.ALWAYS_PUBLIC not in scopes

    def test_view_classes_support_embeds(self):
        for view in VIEW_CLASSES:
            if view in self.EXCLUDED_VIEWS:
                continue
            assert hasattr(view, '_get_embed_partial'), f'{view} lacks embed support'

    def test_view_classes_define_or_override_serializer_class(self):
        for view in VIEW_CLASSES:
            has_serializer_class = getattr(view, 'serializer_class', None) or getattr(view, 'get_serializer_class', None)
            assert has_serializer_class, f'{view} should include serializer class or override get_serializer_class()'

    @mock.patch(
        'osf.models.OSFUser.is_confirmed',
        mock.PropertyMock(return_value=False)
    )
    def test_unconfirmed_user_gets_error(self):

        user = factories.AuthUserFactory()

        res = self.app.get(
            f'/{API_BASE}nodes/',
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch(
        'osf.models.OSFUser.is_disabled',
        mock.PropertyMock(return_value=True)
    )
    def test_disabled_user_gets_error(self):

        user = factories.AuthUserFactory()

        res = self.app.get(
            f'/{API_BASE}nodes/',
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST


class TestStatusView(ApiTestCase):

    def test_status_view(self):
        url = f'/{API_BASE}status/'
        res = self.app.get(url)
        assert res.status_code == 200
        assert 'maintenance' in res.json
        assert res.json['maintenance'] is None

    def test_status_view_with_maintenance(self):
        maintenance.set_maintenance(message='test')
        url = f'/{API_BASE}status/'
        res = self.app.get(url)
        m = maintenance.get_maintenance()
        assert res.status_code == 200
        assert res.json['maintenance']['level'] == 1
        assert res.json['maintenance']['start'] == m['start']
        assert res.json['maintenance']['end'] == m['end']
        assert res.json['maintenance']['message'] == 'test'


class TestJSONAPIBaseView(ApiTestCase):

    def setUp(self):
        super().setUp()

        self.user = factories.AuthUserFactory()
        self.node = factories.ProjectFactory(creator=self.user)
        self.url = f'/{API_BASE}nodes/{self.node._id}/'
        for i in range(5):
            factories.ProjectFactory(parent=self.node, creator=self.user)
        for i in range(5):
            factories.ProjectFactory(parent=self.node)

    @mock.patch(
        'api.base.serializers.JSONAPISerializer.to_representation',
        autospec=True
    )
    def test_request_added_to_serializer_context(self, mock_to_representation):
        self.app.get(self.url, auth=self.user.auth)
        assert 'request' in mock_to_representation.call_args[0][0].context

    def test_reverse_sort_possible(self):
        response = self.app.get(
            'http://localhost:8000/v2/users/me/nodes/?sort=-title',
            auth=self.user.auth
        )
        assert response.status_code == 200


class TestSwaggerDocs(ApiTestCase):

    def test_swagger_docs_redirect_to_root(self):
        res = self.app.get('/v2/docs/')
        assert res.status_code == 302
        assert res.location == '/v2/'
