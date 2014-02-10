import itertools
from website.project.views.node import _view_project
import json


class NodeFileCollector(object):

    """A utility class for creating rubeus formatted node data"""

    def __init__(self, node, auth, parent=None, **kwargs):
        self.node = node
        self.auth = auth
        self.parent = parent
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) if self.can_view else False

    def __call__(self, mode):
        """calls the to_hgrid method"""
        return self.to_hgrid(mode)

    def to_hgrid(self, mode):
        if mode == 'page':
            return self.to_hgrid_page()
        elif mode == 'widget':
            return self.to_hgrid_widget()
        else:
            return self.to_hgrid_other()

    def to_hgrid_page(self):
        rv = _view_project(self.node, self.auth, **self.extra)
        rv.update({
            'grid_data': self._get_grid_data(),
            'tree_js': self._collect_static_js(),
            'tree_css': self._collect_static_css()
        })
        return rv

    def to_hgrid_widget(self):
        return {'grid_data': self._get_grid_data()}

    def to_hgrid_other(self):
        return self._get_grid_data()

    def _collect_components(self, node):
        rv = []
        for child in node.nodes:
            if not child.is_deleted:
                rv.append(self._create_dummy(child))
        return rv

    def _get_grid_data(self):
        return json.dumps(self._collect_addons(self.node) + self._collect_components(self.node))

    def _create_dummy(self, node):
        return {
            'name': 'Component: {0}'.format(node.title) if self.can_view else 'Private Component',
            'kind': 'folder',
            'permissions': {
                'edit': self.can_edit,
                'view': self.can_view
            },
            'urls': {
                'upload': None,
                'fetch': None
            },
            'children': self._collect_addons(node) + self._collect_components(node)
        }

    def _collect_addons(self, node):
        rv = []
        for addon in node.get_addons():
            if addon.config.has_hgrid_files:
                temp = addon.config.get_hgrid_data(addon, self.auth, **self.extra)
                if temp:
                    temp['iconUrl'] = addon.config.icon_url
                    rv.append(temp)
        return rv

    def _collect_static_js(self):
        """Collect JavaScript includes for all add-ons implementing HGrid views.

        :return list: List of JavaScript include paths

        """
        return itertools.chain.from_iterable(
            addon.config.include_js.get('files', [])
            for addon in self.node.get_addons()
        )

    def _collect_static_css(self):
        """Collect Css includes for all addons-ons implementing Hgrid views.

        :return list: List of Css include paths

        """
        return itertools.chain.from_iterable(
            addon.config.include_css.get('files', [])
            for addon in self.node.get_addons()
        )
