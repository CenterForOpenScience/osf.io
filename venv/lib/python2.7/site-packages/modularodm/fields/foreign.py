# -*- coding utf-8 -*-

import abc
import six

from modularodm import signals
from modularodm.fields import Field


@six.add_metaclass(abc.ABCMeta)
class BaseForeignField(Field):

    @abc.abstractmethod
    def get_foreign_object(self, value):
        pass

    def update_backrefs(self, instance, cached_value, current_value):

        if cached_value:
            cached_object = self.get_foreign_object(cached_value)
            if cached_object:
                cached_object._remove_backref(
                    self._backref_field_name,
                    instance,
                    self._field_name
                )

        if current_value:
            current_value._set_backref(
                self._backref_field_name,
                self._field_name,
                instance
            )

    def update_backrefs_callback(self, cls, instance, fields_changed, cached_data):

        if self._field_name not in fields_changed:
            return

        cached_value = cached_data.get(self._field_name)
        current_value = getattr(instance, self._field_name)

        self.update_backrefs(instance, cached_value, current_value)

    def subscribe(self, sender=None):
        self.update_backrefs_callback = signals.save.connect(
            self.update_backrefs_callback,
            sender=sender,
        )
