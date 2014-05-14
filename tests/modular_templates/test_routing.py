import unittest
from framework.routing import Rule, json_renderer


class RuleTestCase(unittest.TestCase):

    def _make_rule(self, **kwargs):
        def vf():
            return {}

        return Rule(
            kwargs.get('routes', ['/', ]),
            kwargs.get('methods', ['GET', ]),
            kwargs.get('view_func_or_data', vf),
            kwargs.get('render_func', json_renderer),
            kwargs.get('view_kwargs'),
        )

    def test_rule_single_route(self):
        r = self._make_rule(routes='/')
        self.assertEqual(r.routes, ['/', ])

    def test_rule_single_method(self):
        r = self._make_rule(methods='GET')
        self.assertEqual(r.methods, ['GET', ])

    def test_rule_lambda_view(self):
        r = self._make_rule(view_func_or_data=lambda: '')
        self.assertTrue(callable(r.view_func_or_data))
