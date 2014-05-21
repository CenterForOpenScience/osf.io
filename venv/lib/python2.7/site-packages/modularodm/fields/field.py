import weakref
import warnings
import copy

from modularodm import exceptions
from modularodm.query.querydialect import DefaultQueryDialect as Q
from .lists import List


def print_arg(arg):
    if isinstance(arg, basestring):
        return '"' + arg + '"'
    return arg


class Field(object):

    default = None
    base_class = None
    _list_class = List
    mutable = False
    lazy_default = True
    _uniform_translator = True

    def __repr__(self):
        return '{cls}({kwargs})'.format(
            cls=self.__class__.__name__,
            kwargs=', '.join('{}={}'.format(key, print_arg(val)) for key, val in self._kwargs.items())
        )

    def subscribe(self, sender=None):
        pass

    def _to_comparable(self):
        return {
            k : v
            for k, v in self.__dict__.items()
            if k not in ['data', '_translators', '_schema_class']
        }

    def __eq__(self, other):
        return self._to_comparable() == other._to_comparable()

    def __ne__(self, other):
        return not self.__eq__(other)

    def _prepare_validators(self, _validate):

        if hasattr(_validate, '__iter__'):

            # List of callable validators
            validate = []
            for validator in _validate:
                if hasattr(validator, '__call__'):
                    validate.append(validator)
                else:
                    raise TypeError('Validator lists must be lists of callables.')

        elif hasattr(_validate, '__call__'):

            # Single callable validator
            validate = _validate

        elif type(_validate) == bool:

            # Boolean validator
            validate = _validate

        else:

            # Invalid validator type
            raise TypeError('Validators must be callables, lists of callables, or booleans.')

        return _validate, validate

    def __init__(self, *args, **kwargs):

        self._args = args
        self._kwargs = kwargs
        self._translators = {}

        # Pointer to containing ListField
        # Set in StoredObject.ObjectMeta
        self._list_container = None

        self.data = weakref.WeakKeyDictionary()

        self._validate, self.validate = \
            self._prepare_validators(kwargs.get('validate', False))

        self._default = kwargs.get('default', self.default)
        self._is_primary = kwargs.get('primary', False)
        self._list = kwargs.get('list', False)
        self._required = kwargs.get('required', False)
        self._unique = kwargs.get('unique', False)
        self._editable = kwargs.get('editable', True)
        self._index = kwargs.get('index', self._is_primary)
        self._is_foreign = False

        # Fields added by ``ObjectMeta``
        self._field_name = None

    def do_validate(self, value, obj):

        # Check if required
        if value is None:
            if getattr(self, '_required', None):
                raise exceptions.ValidationError('Value <{0}> is required.'.format(self._field_name))
            return True

        # Check if unique
        if value is not None and self._unique:
            unique_query = Q(self._field_name, 'eq', value)
            # If object has primary key, don't crash if unique value is
            # already associated with its key
            if obj._is_loaded:
                unique_query = unique_query & Q(obj._primary_name, 'ne', obj._primary_key)
            if obj.find(unique_query).limit(1).count():
                raise exceptions.ValidationValueError('Value must be unique')

        # Field-level validation
        cls = self.__class__
        if hasattr(cls, 'validate') and \
                self.validate != False:
            cls.validate(value)

        # Schema-level validation
        if self._validate and hasattr(self, 'validate'):
            if hasattr(self.validate, '__iter__'):
                for validator in self.validate:
                    validator(value)
            elif hasattr(self.validate, '__call__'):
                self.validate(value)

        # Success
        return True

    def _gen_default(self):
        if callable(self._default):
            return self._default()
        return copy.deepcopy(self._default)

    def _get_translate_func(self, translator, direction):
        try:
            return self._translators[(translator, direction)]
        except KeyError:
            method_name = '%s_%s' % (direction, self.data_type.__name__)
            default_name = '%s_default' % (direction,)
            try:
                method = getattr(translator, method_name)
            except AttributeError:
                method = getattr(translator, default_name)
            self._translators[(translator, direction)] = method
            return method

    def to_storage(self, value, translator=None):
        translator = translator or self._schema_class._translator
        if value is None:
            return translator.null_value
        method = self._get_translate_func(translator, 'to')
        value = value if method is None else method(value)
        if self.mutable:
            return copy.deepcopy(value)
        return value

    def from_storage(self, value, translator=None):
        translator = translator or self._schema_class._translator
        if value == translator.null_value:
            return None
        method = self._get_translate_func(translator, 'from')
        value = value if method is None else method(value)
        if self.mutable:
            return copy.deepcopy(value)
        return value

    def _pre_set(self, instance, safe=False):
        if not self._editable and not safe:
            raise AttributeError('Field cannot be edited.')
        if instance._detached:
            warnings.warn('Accessing a detached record.')

    def __set__(self, instance, value, safe=False, literal=False):
        self._pre_set(instance, safe=safe)
        self.data[instance] = value

    def _touch(self, instance):

        # Reload if dirty
        if instance._dirty:
            instance._dirty = False
            instance.reload()

        # Impute default and return
        try:
            self.data[instance]
        except KeyError:
            self.data[instance] = self._gen_default()

    def __get__(self, instance, owner, check_dirty=True):

        # Warn if detached
        if instance._detached:
            warnings.warn('Accessing a detached record.')

        # Reload if dirty
        self._touch(instance)

        # Impute default and return
        try:
            return self.data[instance]
        except KeyError:
            default = self._gen_default()
            self.data[instance] = default
            return default

    def _get_underlying_data(self, instance):
        """Return data from raw data store, rather than overridden
        __get__ methods. Should NOT be overwritten.
        """
        self._touch(instance)
        return self.data.get(instance, None)

    def __delete__(self, instance):
        self.data.pop(instance, None)
