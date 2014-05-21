# -*- coding: utf-8 -*-

import copy

from modularodm import signals
from ..fields import Field
from ..validators import validate_list


class ListField(Field):

    validate = validate_list

    def __init__(self, field_instance, **kwargs):

        super(ListField, self).__init__(**kwargs)

        self._list_validate, self.list_validate = self._prepare_validators(kwargs.get('list_validate', False))

        # ListField is a list of the following (e.g., ForeignFields)
        self._field_instance = field_instance
        self._is_foreign = field_instance._is_foreign
        self._is_abstract = getattr(field_instance, '_is_abstract', False)
        self._uniform_translator = field_instance._uniform_translator

        # Descriptor data is this type of list
        self._list_class = self._field_instance._list_class

        # Descriptor data is this type of list object, instantiated as our
        # default
        if self._default:
            default = self._default() if callable(self._default) else self._default
            if not hasattr(default, '__iter__') or isinstance(default, dict):
                raise TypeError(
                    'Default value for list fields must be a list; received {0}'.format(
                        type(self._default)
                    )
                )
        else:
            default = None

        #if (self._default
        #    and not hasattr(self._default, '__iter__')
        #    or isinstance(self._default, dict)):
        #    raise TypeError(
        #        'Default value for list fields must be a list; received {0}'.format(
        #            type(self._default)
        #        )
        #    )

        # Default is a callable that returns an empty instance of the list class
        # Avoids the need to deepcopy default values for lists, which will break
        # e.g. when validators contain (un-copyable) regular expressions.
        self._default = lambda: self._list_class(default, base_class=self._field_instance.base_class)

        # Fields added by ``ObjectMeta``
        self._field_name = None

    def subscribe(self, sender=None):
        self.update_backrefs_callback = signals.save.connect(
            self.update_backrefs_callback,
            sender=sender,
        )

    def __set__(self, instance, value, safe=False, literal=False):
        self._pre_set(instance, safe=safe)
        # if isinstance(value, self._default.__class__):
        #     self.data[instance] = value
        if hasattr(value, '__iter__'):
            if literal:
                self.data[instance] = self._list_class(value, base_class=self._field_instance.base_class, literal=True)
            else:
                self.data[instance] = self._list_class(base_class=self._field_instance.base_class)
                self.data[instance].extend(value)
        else:
            self.data[instance] = value

    def do_validate(self, value, obj):

        # Child-level validation
        for part in value:
            self._field_instance.do_validate(part, obj)

        # Field-level list validation
        if hasattr(self.__class__, 'validate'):
            self.__class__.validate(value)

        # Schema-level list validation
        if self._list_validate:
            if hasattr(self.list_validate, '__iter__'):
                for validator in self.list_validate:
                    validator(value)
            elif hasattr(self.list_validate, '__call__'):
                self.list_validate(value)

        # Success
        return True

    def _get_translate_func(self, translator, direction):
        try:
            return self._translators[(translator, direction)]
        except KeyError:
            if self._is_foreign:
                base_class = self._field_instance.base_class
                primary_field = base_class._fields[base_class._primary_name]
                method = primary_field._get_translate_func(translator, direction)
            else:
                method = self._field_instance._get_translate_func(translator, direction)
            self._translators[(translator, direction)] = method
            return method

    def to_storage(self, value, translator=None):
        translator = translator or self._schema_class._translator
        if value:
            if hasattr(value, '_to_data'):
                value = value._to_data()
            if self._uniform_translator:
                method = self._get_translate_func(translator, 'to')
                if method is not None or translator.null_value is not None:
                    value = [
                        translator.null_value if item is None
                        else
                        item if method is None
                        else
                        method(item)
                        for item in value
                    ]
                if self._field_instance.mutable:
                    return copy.deepcopy(value)
                return copy.copy(value)
            else:
                return [
                    self._field_instance.to_storage(item)
                    for item in value
                ]
        return []

    def from_storage(self, value, translator=None):
        translator = translator or self._schema_class._translator
        if value:
            if self._uniform_translator:
                method = self._get_translate_func(translator, 'from')
                if method is not None or translator.null_value is not None:
                    value = [
                        None if item is translator.null_value
                        else
                        item if method is None
                        else
                        method(item)
                        for item in value
                    ]
                if self._field_instance.mutable:
                    return copy.deepcopy(value)
                return copy.copy(value)
            else:
                return [
                    self._field_instance.from_storage(item)
                    for item in value
                ]
        return []

    def update_backrefs(self, instance, cached_value, current_value):

        for item in current_value:
            if self._field_instance.to_storage(item) not in cached_value:
                self._field_instance.update_backrefs(instance, None, item)

        for item in cached_value:
            if self._field_instance.from_storage(item) not in current_value:
                self._field_instance.update_backrefs(instance, item, None)

    def update_backrefs_callback(self, cls, instance, fields_changed, cached_data):

        if not hasattr(self._field_instance, 'update_backrefs'):
            return

        if self._field_name not in fields_changed:
            return

        cached_value = cached_data.get(self._field_name, [])
        current_value = getattr(instance, self._field_name, [])

        self.update_backrefs(instance, cached_value, current_value)

    @property
    def base_class(self):
        if self._field_instance is None:
            return
        if not hasattr(self._field_instance, 'base_class'):
            return
        return self._field_instance.base_class
