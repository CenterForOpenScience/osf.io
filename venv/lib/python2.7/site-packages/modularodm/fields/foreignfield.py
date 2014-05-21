# -*- coding: utf-8 -*-

from modularodm import exceptions

from modularodm.fields.foreign import BaseForeignField
from .lists import ForeignList


class ForeignField(BaseForeignField):

    _list_class = ForeignList

    def __init__(self, *args, **kwargs):

        super(ForeignField, self).__init__(*args, **kwargs)

        self._backref_field_name = kwargs.get('backref', None)
        self._base_class_reference = args[0]
        self._base_class = None
        self._is_foreign = True
        self._is_abstract = False

    def get_foreign_object(self, value):
        return self.base_class.load(value)

    def to_storage(self, value, translator=None):

        if value is None:
            return value
        try:
            value_to_store = value._primary_key
        except AttributeError:
            value_to_store = value
        _foreign_pn = self.base_class._primary_name
        return self.base_class._fields[_foreign_pn].to_storage(value_to_store, translator)

    def from_storage(self, value, translator=None):

        if value is None:
            return None
        _foreign_pn = self.base_class._primary_name
        _foreign_pk = self.base_class._fields[_foreign_pn].from_storage(value, translator)
        return _foreign_pk

    def _to_primary_key(self, value):
        """
        Return primary key; if value is StoredObject, verify
        that it is loaded.

        """
        if value is None:
            return None
        if isinstance(value, self.base_class):
            if not value._is_loaded:
                raise exceptions.DatabaseError('Record must be loaded.')
            return value._primary_key

        return self.base_class._to_primary_key(value)
        # return self.base_class._check_pk_type(value)

    @property
    def mutable(self):
        return self.base_class._fields[self.base_class._primary_name].mutable

    @property
    def base_class(self):
        if self._base_class:
            return self._base_class
        if isinstance(self._base_class_reference, type):
            self._base_class = self._base_class_reference
        else:
            try:
                self._base_class = self._schema_class.get_collection(
                    self._base_class_reference
                )
            except KeyError:
                raise exceptions.ModularOdmException(
                    'Unknown schema "{0}"'.format(
                        self._base_class_reference
                    )
                )
        return self._base_class

    def __set__(self, instance, value, safe=False, literal=False):
        # if instance._detached:
        #     warnings.warn('Accessing a detached record.')
        value_to_set = value if literal else self._to_primary_key(value)
        super(ForeignField, self).__set__(
            instance,
            value_to_set,
            safe=safe
        )

    def __get__(self, instance, owner):
        # if instance._detached:
        #     warnings.warn('Accessing a detached record.')
        primary_key = super(ForeignField, self).__get__(instance, None)
        if primary_key is None:
            return
        return self.base_class.load(primary_key)
