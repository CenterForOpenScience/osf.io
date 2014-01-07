"""

"""

import os
import glob
import importlib
import mimetypes
from bson import ObjectId
from mako.lookup import TemplateLookup

from framework import StoredObject, fields
from framework.routing import process_rules

from website import settings

lookup = TemplateLookup(
    directories=[
        settings.TEMPLATES_PATH
    ]
)

class AddonError(Exception): pass


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
                 widget_help=None, has_page=False, has_widget=False, **kwargs):

        self.settings_model = settings_model
        self.settings_model.config = self

        self.short_name = short_name
        self.full_name = full_name
        self.added_by_default = added_by_default
        self.categories = categories
        self.schema = schema

        self.include_js = self._include_to_static(include_js or {})
        self.include_css = self._include_to_static(include_css or {})

        self.widget_help = widget_help

        self.has_page = has_page
        self.has_widget = has_widget

        # Build back-reference key
        self.backref_key = '__'.join([self.settings_model._name, 'addons'])

        # Build template lookup
        template_path = os.path.join('website', 'addons', short_name, 'templates')
        if os.path.exists(template_path):
            self.template_lookup = TemplateLookup(
                directories=[
                    template_path,
                    settings.TEMPLATES_PATH,
                ]
            )
        else:
            self.template_lookup = None

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
        return self._static_url(self.icon) if self.icon else None

    def to_json(self):

        return {
            'short_name': self.short_name,
            'full_name': self.full_name,
            'help': self.widget_help,
            'icon': self.icon_url,
            'has_page': self.has_page,
            'has_widget': self.has_widget,
        }


class AddonSettingsBase(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    node = fields.ForeignField('node', backref='addons')
    registered = fields.BooleanField()

    _meta = {
        'abstract': True,
    }

    def render_config_error(self, data):
        """

        """
        # Note: `config` is added to `self` in AddonConfig::__init__.
        template = lookup.get_template('project/addon/config_error.mako')
        return template.get_def('config_error').render(
            title=self.config.full_name,
            name=self.config.short_name,
            **data
        )

    #############
    # Callbacks #
    #############

    def before_page_load(self, node, user):
        """

        :param Node node:
        :param User user:

        """
        pass

    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        pass

    def after_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:

        """
        pass

    def after_set_permissions(self, node, permissions):
        """

        :param Node node:
        :param str permissions:

        """
        pass

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node:
        :param Node fork:
        :param User user:
        :param bool save:
        :return AddonSettingsBase:

        """
        clone = self.clone()
        clone.node = fork

        if save:
            clone.save()

        return clone

    def after_register(self, node, registration, user, save=True):
        """

        :param Node node:
        :param Node registration:
        :param User user:
        :param bool save:
        :return AddonSettingsBase:

        """
        clone = self.clone()
        clone.node = registration

        if save:
            clone.save()

        return clone


# TODO: Move this
LOG_TEMPLATES = 'website/templates/log_templates.mako'


def init_addon(app, addon_name, routes=True):
    """Load addon module and create configuration object.

    :param app: Flask app object
    :param addon_name: Name of addon directory
    :param bool routes: Add routes
    :return AddonConfig: AddonConfig configuration object if module found,
        else None

    """
    addon_path = os.path.join('website', 'addons', addon_name)
    template_path = os.path.join(addon_path, 'templates')
    import_path = 'website.addons.{0}'.format(addon_name)
    views_import_path = '{0}.views'.format(import_path)

    # Import addon module
    try:
        addon_module = importlib.import_module(import_path)
    except ImportError:
        return None

    data = vars(addon_module)

    try:
        addon_views = importlib.import_module(views_import_path)
        has_page = hasattr(addon_views, '{0}_page'.format(addon_name))
        has_widget = hasattr(addon_views, '{0}_widget'.format(addon_name))
    except ImportError:
        has_page = False
        has_widget = False

    has_page = has_page or data.pop('HAS_PAGE', False)

    # Append add-on log templates to main log templates
    log_templates = os.path.join(
        addon_path, 'templates', 'log_templates.mako'
    )
    if os.path.exists(log_templates):
        with open(LOG_TEMPLATES, 'a') as fp:
            fp.write(open(log_templates, 'r').read())

    # Add routes
    if routes:
        for route_group in getattr(addon_module, 'ROUTES', []):
            process_rules(app, **route_group)

    # Build AddonConfig object
    return AddonConfig(
        has_page=has_page,
        has_widget=has_widget,
        **{
            key.lower(): value
            for key, value in data.iteritems()
        }
    )
