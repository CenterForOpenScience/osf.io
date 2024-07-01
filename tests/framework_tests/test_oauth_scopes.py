from unittest import TestCase

from framework.auth import oauth_scopes

class TestOAuthScopes(TestCase):

    def test_each_public_scope_includes_ALWAYS_PUBLIC(self):
        for scope in oauth_scopes.public_scopes.values():
            assert oauth_scopes.CoreScopes.ALWAYS_PUBLIC in scope.parts
