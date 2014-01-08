"""

"""

from framework import StoredObject, fields
from website import settings


class AddonModelMixin(StoredObject):

    addons_enabled = fields.StringField(list=True)
    _meta = {
        'abstract': True,
    }

    def _ensure_addons(self):

        for addon in self.addons_enabled:

            addon_config = settings.ADDONS_AVAILABLE_DICT[addon]
            Schema = addon_config.models[self._name]
            backref_key = self._backref_key(addon_config)
            models = getattr(self, backref_key)
            if not models:
                model = Schema(owner=self)
                model.save()

    def _order_addons(self):
        """Ensure that addons in `addons_enabled` appear in the same order as
        in `ADDONS_AVAILABLE`.

        """
        self.addons_enabled = [
            addon.short_name
            for addon in settings.ADDONS_AVAILABLE
            if addon.short_name in self.addons_enabled
        ]

    def _backref_key(self, addon_config):

        return '{0}__addons'.format(
            addon_config.models[self._name]._name,
        )

    def get_addon(self, addon_name):
        """Get addon for node.

        :param str addon_name: Name of addon
        :return AddonNodeSettingsBase: Settings record

        """
        addon_config = settings.ADDONS_AVAILABLE_DICT.get(addon_name)
        if not addon_config or not addon_config.models[self._name]:
            return False

        backref_key = self._backref_key(addon_config)
        addons = getattr(self, backref_key)
        if addons:
            return addons[0]


    def add_addon(self, addon_name, save=True):
        """Add an add-on to the node.

        :param str addon_name: Name of add-on
        :return bool: Add-on was added

        """
        if addon_name in self.addons_enabled:
            return False

        addon_config = settings.ADDONS_AVAILABLE_DICT.get(addon_name)
        if not addon_config or not addon_config.models[self._name]:
            return False

        if addon_name not in self.addons_enabled:
            self.addons_enabled.append(addon_name)
            self._order_addons()
            if save:
                self.save()

        backref_key = self._backref_key(addon_config)
        models = getattr(self, backref_key)
        if not models:
            model = addon_config.models[self._name](owner=self)
            model.save()

        return True

    def delete_addon(self, addon_name, save=True):
        """Delete an add-on from the node.

        :param str addon_name: Name of add-on
        :return bool: Add-on was deleted

        """
        try:
            self.addons_enabled.remove(addon_name)
            if save:
                self.save()
            return True
        except ValueError:
            return False
