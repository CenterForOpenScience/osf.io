# -*- coding: utf-8 -*-
import httplib as http
import sys
import inspect
import pkgutil

import mock

from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests import factories

from api.base.settings.defaults import API_BASE
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from api.base.permissions import TokenHasScope

from framework.auth.oauth_scopes import CoreScopes

class TestApiBaseViews(ApiTestCase):

    def test_root_returns_200(self):
        res = self.app.get('/{}'.format(API_BASE))
        assert_equal(res.status_code, 200)

    def test_view_classes_have_minimal_set_of_permissions_classes(self):
        base_permissions = [            
            TokenHasScope,
            (IsAuthenticated, IsAuthenticatedOrReadOnly)
        ]
        view_modules = [name for _, name, _ in pkgutil.iter_modules(['api'])]
        for module in view_modules:
            for name, view in inspect.getmembers(sys.modules['api.{}.views'.format(module)], inspect.isclass):
                if hasattr(view, 'permission_classes'):
                    for cls in base_permissions:
                        if isinstance(cls, tuple):
                            has_cls = any([c in view.permission_classes for c in cls])
                            assert_true(has_cls, "{0} lacks the appropriate permission classes".format(name))
                        else:
                            assert_in(cls, view.permission_classes, "{0} lacks the appropriate permission classes".format(name))
                        for key in ['read', 'write']:                            
                            scopes = getattr(view, 'required_{}_scopes'.format(key), None)
                            assert_true(bool(scopes))
                            for scope in scopes:
                                assert_is_not_none(scope)                        

    @mock.patch('framework.auth.core.User.is_confirmed', mock.PropertyMock(return_value=False))
    def test_unconfirmed_user_gets_error(self):

        user = factories.AuthUserFactory()

        res = self.app.get('/{}nodes/'.format(API_BASE), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        
    @mock.patch('framework.auth.core.User.is_disabled', mock.PropertyMock(return_value=True))
    def test_disabled_user_gets_error(self):

        user = factories.AuthUserFactory()

        res = self.app.get('/{}nodes/'.format(API_BASE), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        
