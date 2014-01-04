"""

"""

import httplib as http

from framework.exceptions import HTTPError
from framework.routing import Rule, json_renderer
from website.project import decorators


def disable_view_factory(addon):

    @decorators.must_be_contributor
    @decorators.must_have_addon(addon)
    def disable(*args, **kwargs):
        node = kwargs['node'] or kwargs['project']
        try:
            node.addons_enabled.remove('github')
        except ValueError:
            raise HTTPError(http.BAD_REQUEST)
        node.save()

    disable.__name__ = '{0}_disable'.format(addon)
    return disable


def disable_rule_factory(addon):
    return Rule(
        [
            '/project/<pid>/settings/{0}/disable/'.format(addon),
            '/project/<pid>/node/<nid>/settings/{0}/disable/'.format(addon),
        ],
        'post',
        disable_view_factory(addon),
        json_renderer,
    )