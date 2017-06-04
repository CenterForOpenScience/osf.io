# -*- coding: utf-8 -*-
from nose.tools import assert_in
from unittest import TestCase

from framework.auth import oauth_scopes

class TestOAuthScopes(TestCase):

    def test_each_public_scope_includes_ALWAYS_PUBLIC(self):
        for scope in oauth_scopes.public_scopes.itervalues():
            assert_in(oauth_scopes.CoreScopes.ALWAYS_PUBLIC, scope.parts)
