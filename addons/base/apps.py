from django.apps import AppConfig


class BaseAddonConfig(AppConfig):
    name = 'addons.base'

    actions = tuple()
    user_settings = None
    node_settings = None
    node_settings_template = 'TODO'

    @property
    def full_name(self):
        raise NotImplementedError
