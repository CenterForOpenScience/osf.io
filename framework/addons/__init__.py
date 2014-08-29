# -*- coding: utf-8 -*-

from framework.mongo import StoredObject
from website import settings


class AddonModelMixin(StoredObject):

    _meta = {
        'abstract': True,
    }

    def get_addons(self):
        addons = []
        for addon_name in settings.ADDONS_AVAILABLE_DICT.keys():
            addon = self.get_addon(addon_name)
            if addon:
                addons.append(addon)
        return addons

    def get_addon_names(self):
        return [
            addon.config.short_name
            for addon in self.get_addons()
        ]

    def _backref_key(self, addon_config):
        return '{0}__addons'.format(
            addon_config.settings_models[self._name]._name,
        )

    def get_addon(self, addon_name, deleted=False):
        """Get addon for node.

        :param str addon_name: Name of addon
        :return: Settings record if found, else None

        """
        addon_config = settings.ADDONS_AVAILABLE_DICT.get(addon_name)
        if not addon_config or not addon_config.settings_models.get(self._name):
            return False

        backref_key = self._backref_key(addon_config)
        addons = [
            addon for addon in getattr(self, backref_key)
            if addon is not None
        ]
        if addons:
            if deleted or not addons[0].deleted:
                assert len(addons) == 1, 'Violation of one-to-one mapping with addon model'
                return addons[0]
        return None

    def has_addon(self, addon_name, deleted=False):
        return bool(self.get_addon(addon_name, deleted=deleted))

    def add_addon(self, addon_name, auth=None, override=False, _force=False):
        """Add an add-on to the node.

        :param str addon_name: Name of add-on
        :param Auth auth: Consolidated authorization object
        :param bool override: For shell use only, Allows adding of system addons
        :param bool __force: For migration testing ONLY. Do not set to True
            in the application, or else project's will be allowed to have
            duplicate addons!
        :return bool: Add-on was added

        """

        if not override and addon_name in settings.SYSTEM_ADDED_ADDONS[self._name]:
            return False

        # Reactivate deleted add-on if present
        addon = self.get_addon(addon_name, deleted=True)
        if addon:
            if addon.deleted:
                addon.undelete(save=True)
                return True
            if not _force:
                return False

        # Get add-on settings model
        addon_config = settings.ADDONS_AVAILABLE_DICT.get(addon_name)
        if not addon_config or not addon_config.settings_models[self._name]:
            return False

        # Instantiate model
        model = addon_config.settings_models[self._name](owner=self)
        model.on_add()
        model.save()

        return True

    def delete_addon(self, addon_name, auth=None):
        """Delete an add-on from the node.

        :param str addon_name: Name of add-on
        :param Auth auth: Consolidated authorization object
        :return bool: Add-on was deleted

        """
        addon = self.get_addon(addon_name)
        if addon:
            if self._name in addon.config.added_mandatory:
                raise ValueError('Cannot delete mandatory add-on.')
            addon.delete(save=True)
            return True
        return False

    def config_addons(self, config, auth=None, save=True):
        """Enable or disable a set of add-ons.

        :param dict config: Mapping between add-on names and enabled / disabled
            statuses

        """

        for addon_name, enabled in config.iteritems():
            if enabled:
                self.add_addon(addon_name, auth)
            else:
                self.delete_addon(addon_name, auth)
        if save:
            self.save()
