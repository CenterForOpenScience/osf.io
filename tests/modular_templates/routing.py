import unittest
from new_style import Rule


class RuleTestCase(unittest.TestCase):

    def _make_rule(self, **kwargs):
        def vf():
            return {}

        return Rule(
            kwargs.get('routes', ['/', ]),
            kwargs.get('methods', ['GET', ]),
            kwargs.get('view_func', vf),
            kwargs.get('render_func'),
            kwargs.get('view_kwargs'),
        )

    def test_rule_single_route(self):
        r = self._make_rule(routes='/')
        self.assertEqual(r.routes, ['/', ])

    def test_rule_single_method(self):
        r = self._make_rule(methods='GET')
        self.assertEqual(r.methods, ['GET', ])

    def test_rule_lambda_view(self):
        r = self._make_rule(view_func=lambda: '')
        self.assertTrue(callable(r.view_func))