# -*- coding: utf-8 -*-
from nose.tools import assert_in
from tests.base import OsfTestCase

from framework.auth import oauth_scopes


class TestOAuthScopes(OsfTestCase):

    def test_each_public_scope_includes_ALWAYS_PUBLIC(self):
        for scope in oauth_scopes.public_scopes.values():
            assert_in(oauth_scopes.CoreScopes.ALWAYS_PUBLIC, scope.parts)
