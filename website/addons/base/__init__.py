"""

"""

import os
import glob
import importlib
import mimetypes
from bson import ObjectId

from framework import StoredObject, fields
from framework.routing import process_rules


def _is_image(filename):
    mtype, _ = mimetypes.guess_type(filename)
    return mtype and mtype.startswith('image')


class AddonConfig(object):

    def _static_url(self, filename):
        """Build static URL for file; use the current addon if relative path,
        else the global static directory.

        :param str filename: Local path to file
        :return str: Static URL for file

        """
        if filename.startswith('/'):
            return filename
        return '/addons/static/{addon}/{filename}'.format(
            addon=self.short_name,
            filename=filename,
        )

    def _include_to_static(self, include):
        """

        """
        return {
            key: [
                self._static_url(item)
                for item in value
            ]
            for key, value in include.iteritems()
        }

    def __init__(self, settings_model, short_name, full_name, added_by_default,
                 categories, schema=None, include_js=None, include_css=None,
                 widget_help=None, **kwargs):

        # Memorize arguments
        self.settings_model = settings_model
        self.short_name = short_name
        self.full_name = full_name
        self.added_by_default = added_by_default
        self.categories = categories
        self.schema = schema

        self.include_js = self._include_to_static(include_js or {})
        self.include_css = self._include_to_static(include_css or {})

        self.widget_help = widget_help

        # Build back-reference key
        self.backref_key = '__'.join([self.settings_model._name, 'addons'])

    @property
    def icon(self):

        try:
            return self._icon
        except:
            static_path = os.path.join('website', 'addons', self.short_name, 'static')
            static_files = glob.glob(os.path.join(static_path, 'comicon.*'))
            image_files = [
                os.path.split(filename)[1]
                for filename in static_files
                if _is_image(filename)
            ]
            if len(image_files) == 1:
                self._icon = image_files[0]
            else:
                self._icon = None
            return self._icon

    @property
    def icon_url(self):
        return self._static_url(self.icon)

    def widget_json(self, settings_model):

        try:
            return {
                'name': self.short_name,
                'title': self.full_name,
                'help': self.widget_help,
                'page': hasattr(settings_model, 'render_page'),
                'content': settings_model.render_widget(),
            }
        except NotImplementedError:
            return None


class AddonSettingsBase(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    node = fields.ForeignField('node', backref='addons')

    _meta = {
        'abstract': True,
    }

    #def render_widget(self):
    #    raise NotImplementedError
    #
    #def render_tab(self):
    #    raise NotImplementedError
    #
    #def render_page(self):
    #    raise NotImplementedError


def init_addon(app, addon_name):
    """Load addon module and create a configuration object

    :param app: Flask app object
    :param addon_name: Name of addon directory
    :return AddonConfig: AddonConfig configuration object if module found, else None

    """
    addon_path = 'website.addons.{0}'.format(addon_name)

    # Import addon module
    try:
        addon_module = importlib.import_module(addon_path)
    except ImportError:
        return None

    # Add routes
    for route_group in getattr(addon_module, 'ROUTES', []):
        process_rules(app, **route_group)

    # Build AddonConfig object
    return AddonConfig(**{
        key.lower(): value
        for key, value in vars(addon_module).iteritems()
    })
