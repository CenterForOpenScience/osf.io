# -*- coding: utf-8 -*-

import six
import copy
import logging
import warnings
from functools import wraps

from . import signals
from . import exceptions
from fields import Field, ListField, ForeignList, AbstractForeignList
from .storage import Storage
from .query import QueryBase, RawQuery, QueryGroup
from .frozen import FrozenDict
from .cache import Cache
from .writequeue import WriteQueue, WriteAction


logger = logging.getLogger(__name__)


class ContextLogger(object):

    @staticmethod
    def sort_func(e):
        return (e.xtra._name if e.xtra else None, e.func.__name__)

    def report(self, sort_func=None):
        return self.logger.report(sort_func or self.sort_func)

    def __init__(self, log_level=None, xtra=None, sort_func=None):
        self.log_level = log_level
        self.xtra = xtra
        self.sort_func = sort_func or self.sort_func
        self.logger = Storage.logger

    def __enter__(self):
        self.listening = self.logger.listen(self.xtra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.listening:
            report = self.logger.report(
                lambda e: (e.xtra._name if e.xtra else None, e.func.__name__)
            )
            if self.log_level is not None:
                logging.log(self.log_level, report)
            self.logger.clear()
        self.logger.pop()


def deref(data, keys, missing=None):
    if keys[0] in data:
        if len(keys) == 1:
            return data[keys[0]]
        return deref(data[keys[0]], keys[1:], missing=missing)
    return missing


def flatten_backrefs(data, stack=None):

    stack = stack or []

    if isinstance(data, list):
        return [(stack, item) for item in data]

    out = []
    for key, val in data.items():
        out.extend(flatten_backrefs(val, stack + [key]))

    return out


def log_storage(func):

    @wraps(func)
    def wrapped(this, *args, **kwargs):

        cls = this if isinstance(this, type) else type(this)

        with ContextLogger(log_level=this._log_level, xtra=cls):
            return func(this, *args, **kwargs)

    return wrapped


def warn_if_detached(func):
    """ Warn if self / cls is detached. """
    @wraps(func)
    def wrapped(this, *args, **kwargs):
        # Check for _detached in __dict__ instead of using hasattr
        # to avoid infinite loop in __getattr__
        if '_detached' in this.__dict__ and this._detached:
            warnings.warn('here')
        return func(this, *args, **kwargs)
    return wrapped


def has_storage(func):
    """ Ensure that self/cls contains a Storage backend. """
    @wraps(func)
    def wrapped(*args, **kwargs):
        me = args[0]
        if not hasattr(me, '_storage') or \
                not me._storage:
            raise exceptions.ImproperConfigurationError(
                'No storage backend attached to schema <{0}>.'
                    .format(me._name.upper())
            )
        return func(*args, **kwargs)
    return wrapped


class ObjectMeta(type):

    def add_field(cls, name, field):

        # Skip if not descriptor
        if not isinstance(field, Field):
            return

        # Memorize parent references
        field._schema_class = cls
        field._field_name = name

        # Check for primary key
        if field._is_primary:
            if cls._primary_name is None:
                cls._primary_name = name
                cls._primary_type = field.data_type
            else:
                raise AttributeError(
                    'Multiple primary keys are not supported.')

        # Wrap in list
        if field._list and not isinstance(field, ListField):
            field = ListField(
                field,
                **field._kwargs
            )
            # Memorize parent references
            field._schema_class = cls
            field._field_name = name
            # Set parent pointer of child field to list field
            field._field_instance._list_container = field

        # Subscribe to schema events
        field.subscribe(sender=cls)

        # Store descriptor to cls, cls._fields
        setattr(cls, name, field)
        cls._fields[name] = field

    def __init__(cls, name, bases, dct):

        # Run super-metaclass __init__
        super(ObjectMeta, cls).__init__(name, bases, dct)

        # Store prettified name
        cls._name = name.lower()

        # Store parameters from _meta
        my_meta = cls.__dict__.get('_meta', {})

        cls._is_optimistic = my_meta.get('optimistic', False)
        cls._is_abstract = my_meta.get('abstract', False)
        cls._log_level = my_meta.get('log_level', None)
        cls._version_of = my_meta.get('version_of', None)
        cls._version = my_meta.get('version', 1)

        # Prepare fields
        cls._fields = {}
        cls._primary_name = None
        cls._primary_type = None

        for key, value in cls.__dict__.items():
            cls.add_field(key, value)

        for base in bases:
            if not hasattr(base, '_fields') or not isinstance(base._fields, dict):
                continue
            for key, value in base._fields.items():
                cls.add_field(key, copy.deepcopy(value))

        # Impute field named _id as primary if no primary field specified;
        # must be exactly one primary field unless abstract
        if cls._fields:
            cls._is_root = False
            if cls._primary_name is None:
                if '_id' in cls._fields:
                    primary_field = cls._fields['_id']
                    primary_field._is_primary = True
                    if 'index' not in primary_field._kwargs or not primary_field._kwargs['index']:
                        primary_field._index = True
                    cls._primary_name = '_id'
                    cls._primary_type = cls._fields['_id'].data_type
                elif not cls._is_abstract:
                    raise AttributeError(
                        'Schemas must either define a field named _id or '
                        'specify exactly one field as primary.')
            # Register
            cls.register_collection()
        else:
            cls._is_root = True

    @property
    def _translator(cls):
        return cls._storage[0].translator


@six.add_metaclass(ObjectMeta)
class StoredObject(object):

    _collections = {}

    _cache = Cache()
    _object_cache = Cache()
    queue = WriteQueue()

    def __init__(self, **kwargs):

        # Crash if abstract
        if self._is_abstract:
            raise TypeError('Cannot instantiate abstract schema')

        self.__backrefs = {}
        self._dirty = False
        self._detached = False
        self._is_loaded = kwargs.pop('_is_loaded', False)
        self._stored_key = None

        # Impute non-lazy default values (e.g. datetime with auto_now=True)
        for value in self._fields.values():
            if not value.lazy_default:
                value.__set__(self, value._gen_default(), safe=True)

        # Add kwargs to instance
        for key, value in kwargs.items():
            try:
                field = self._fields[key]
                field.__set__(self, value, safe=True)
            except KeyError:
                if key == '__backrefs':
                    key = '_StoredObject__backrefs'
                setattr(self, key, value)

        if self._is_loaded:
            self._set_cache(self._primary_key, self)

    def __eq__(self, other):
        try:
            if self is other:
                return True
            return self.to_storage() == other.to_storage()
        except (AttributeError, TypeError):
            # Can't compare with "other". Try the reverse comparison
            return NotImplemented

    def __ne__(self, other):
        try:
            if self is other:
                return False
            return self.to_storage() != other.to_storage()
        except (AttributeError, TypeError):
            # Can't compare with "other". Try the reverse comparison
            return NotImplemented

    @warn_if_detached
    def __unicode__(self):
        return unicode({field : unicode(getattr(self, field)) for field in self._fields})

    @warn_if_detached
    def __str__(self):
        return unicode(self).decode('ascii', 'replace')

    @classmethod
    def register_collection(cls):
        cls._collections[cls._name] = cls

    @classmethod
    def get_collection(cls, name):
        return cls._collections[name.lower()]

    @property
    def _primary_key(self):
        return getattr(self, self._primary_name)

    @_primary_key.setter
    def _primary_key(self, value):
        setattr(self, self._primary_name, value)

    @property
    def _storage_key(self):
        """ Primary key passed through translator. """
        return self._pk_to_storage(self._primary_key)

    @property
    @has_storage
    def _translator(self):
        return self.__class__._translator

    @has_storage
    def to_storage(self, translator=None, clone=False):

        data = {}

        for field_name, field_object in self._fields.items():

            # Ignore primary and foreign fields if cloning
            # TODO: test this
            if clone:
                if field_object._is_primary or field_object._is_foreign:
                    continue
            field_value = field_object.to_storage(
                field_object._get_underlying_data(self),
                translator
            )
            data[field_name] = field_value

        data['_version'] = self._version
        if not clone and self.__backrefs:
            data['__backrefs'] = self.__backrefs

        return data

    @classmethod
    @has_storage
    def from_storage(cls, data, translator=None):

        result = {}

        for key, value in data.items():

            field_object = cls._fields.get(key, None)

            if isinstance(field_object, Field):
                data_value = data[key]
                if data_value is None:
                    value = None
                    result[key] = None
                else:
                    value = field_object.from_storage(data_value, translator)
                result[key] = value

            else:
                result[key] = value

        return result

    def clone(self):
        return self.load(
            data=self.to_storage(clone=True),
            _is_loaded=False
        )

    # Backreferences

    @property
    def _backrefs(self):
        return FrozenDict(**self.__backrefs)

    @_backrefs.setter
    def _backrefs(self, _):
        raise exceptions.ModularOdmException('Cannot modify _backrefs.')

    @property
    def _backrefs_flat(self):
        return flatten_backrefs(self.__backrefs)

    def _remove_backref(self, backref_key, parent, parent_field_name, strict=False):
        try:
            self.__backrefs[backref_key][parent._name][parent_field_name].remove(parent._primary_key)
            self.save(force=True)
        except ValueError:
            if strict:
                raise

    def _update_backref(self, backref_key, parent, parent_field_name):
        updated = False
        try:
            refs = self.__backrefs[backref_key][parent._name][parent_field_name]
            if refs[refs.index(parent._stored_key)] != parent._primary_key:
                refs[refs.index(parent._stored_key)] = parent._primary_key
                updated = True
        except (KeyError, ValueError):
            self._set_backref(backref_key, parent_field_name, parent)
            return True
        if updated:
            self.save(force=True)
            return True
        return False

    def _set_backref(self, backref_key, parent_field_name, backref_value):

        backref_value_class_name = backref_value.__class__._name
        backref_value_primary_key = backref_value._primary_key

        if backref_value_primary_key is None:
            raise exceptions.DatabaseError('backref object\'s primary key must be saved first')

        if backref_key not in self.__backrefs:
            self.__backrefs[backref_key] = {}
        if backref_value_class_name not in self.__backrefs[backref_key]:
            self.__backrefs[backref_key][backref_value_class_name] = {}
        if parent_field_name not in self.__backrefs[backref_key][backref_value_class_name]:
            self.__backrefs[backref_key][backref_value_class_name][parent_field_name] = []

        append_to = self.__backrefs[backref_key][backref_value_class_name][parent_field_name]
        if backref_value_primary_key not in append_to:
            append_to.append(backref_value_primary_key)

        self.save(force=True)

    @classmethod
    def set_storage(cls, storage):

        if not isinstance(storage, Storage):
            raise TypeError('Argument to set_storage must be an instance of Storage.')
        if not hasattr(cls, '_storage'):
            cls._storage = []

        for field_name, field_object in cls._fields.items():
            if field_object._index:
                storage._ensure_index(field_name)

        cls._storage.append(storage)

    # Caching ################################################################

    @classmethod
    def _is_cached(cls, key):
        return cls._object_cache.get(cls._name, key) is not None

    @classmethod
    def _load_from_cache(cls, key):
        trans_key = cls._pk_to_storage(key)
        return cls._object_cache.get(cls._name, trans_key)

    @classmethod
    def _set_cache(cls, key, obj):

        trans_key = cls._pk_to_storage(key)
        cls._object_cache.set(cls._name, trans_key, obj)
        cls._cache.set(cls._name, trans_key, obj.to_storage())

    @classmethod
    def _get_cache(cls, key):
        trans_key = cls._pk_to_storage(key)
        return cls._object_cache.get(cls._name, trans_key)

    @classmethod
    def _get_cached_data(cls, key):
        return cls._cache.get(cls._name, key)

    def get_changed_fields(self, cached_data, storage_data):
        """Get fields that differ between the cache_sandbox and the current object.
        Validation and after_save methods should only be run on diffed
        fields.

        :param cached_data: Storage-formatted data from cache_sandbox
        :param storage_data: Storage-formatted data from object
        :return: List of diffed fields

        """
        if not self._is_loaded or cached_data is None:
            return []

        return [
            field
            for field in self._fields
            if cached_data[field] != storage_data[field]
        ]

    # Cache clearing

    @classmethod
    def _clear_data_cache(cls, key=None):
        if not cls._fields:
            cls._cache.clear()
        elif key is not None:
            cls._cache.pop(cls._name, key)
        else:
            cls._cache.clear_schema(cls._name)

    @classmethod
    def _clear_object_cache(cls, key=None):
        if not cls._fields:
            cls._object_cache.clear()
        elif key is not None:
            cls._object_cache.pop(cls._name, key)
        else:
            cls._object_cache.clear_schema(cls._name)

    @classmethod
    def _clear_caches(cls, key=None):
        cls._clear_data_cache(key)
        cls._clear_object_cache(key)

    ###########################################################################

    @classmethod
    def _to_primary_key(cls, value):

        if value is None:
            return value

        if isinstance(value, cls):
            return value._primary_key

        return cls._check_pk_type(value)

    @classmethod
    def _check_pk_type(cls, key):

        if isinstance(key, cls._primary_type):
            return key

        try:
            cls._primary_type()
            cast_type = cls._primary_type
        except:
            cast_type = str

        try:
            key = cast_type(key)
        except:
            raise TypeError(
                'Invalid key type: {key}, {type}, {ptype}.'.format(
                    key=key, type=type(key), ptype=cast_type
                )
            )

        return key

    @classmethod
    @has_storage
    @log_storage
    def load(cls, key=None, data=None, _is_loaded=True):
        '''Get a record by its primary key.'''

        # Emit load signal
        signals.load.send(
            cls,
            key=key,
            data=data,
        )

        if key is not None:
            key = cls._check_pk_type(key)
            cached_object = cls._load_from_cache(key)
            if cached_object is not None:
                return cached_object

        # Try loading from backend
        if data is None:
            data = cls._storage[0].get(cls._primary_name, cls._pk_to_storage(key))

        # if not found, return None
        if data is None:
            return None

        # Convert storage data to ODM
        data = cls.from_storage(data)

        if '_version' in data and data['_version'] != cls._version:

            old_object = cls._version_of.load(data=data)
            new_object = cls(_is_loaded=_is_loaded)

            cls.migrate(old_object, new_object)
            new_object._stored_key = new_object._primary_key

            return new_object

        rv = cls(_is_loaded=_is_loaded, **data)
        rv._stored_key = rv._primary_key

        return rv

    @classmethod
    def migrate_all(cls):
        """Migrate all records in this collection."""
        for record in cls.find():
            record.save()

    @classmethod
    def migrate(cls, old, new, verbose=True, dry_run=False, rm_refs=True):
        """Migrate record to new schema.

        :param old: Record from original schema
        :param new: Record from new schema
        :param verbose: Print detailed info
        :param dry_run: Dry run; make no changes if true
        :param rm_refs: Remove references on deleted fields

        """
        if verbose:
            logging.basicConfig(format='%(levelname)s %(filename)s: %(message)s',
                                level=logging.DEBUG)
        # Check deleted, added fields
        deleted_fields = [field for field in old._fields if field not in new._fields]
        added_fields = [field for field in new._fields if field not in old._fields]
        logging.info('Will delete fields: {0}'.format(deleted_fields))
        logging.info('Will add fields: {0}'.format(added_fields))

        # Check change in primary key
        if old._primary_name != new._primary_name:
            logging.info("The primary key will change from {old_name}: {old_field} to "
                "{new_name}: {new_field} in this migration. Primary keys and "
                "backreferences will not be automatically migrated. If you want "
                "to migrate primary keys, you should handle this in your "
                "migrate() method."
                    .format(old_name=old._primary_name,
                            old_field=old._fields[old._primary_name],
                            new_name=new._primary_name,
                            new_field=new._fields[new._primary_name]))

        # Copy fields to new object
        for field in old._fields:

            # Delete forward references on deleted fields
            if field not in cls._fields:
                if rm_refs:
                    logging.info("Backreferences to this object keyed on foreign "
                        "field {name}: {field} will be deleted in this migration. "
                        "To prevent this behavior, re-run with <rm_fwd_refs> "
                        "set to False.".format(name=field,
                                              field=old._fields[field]))
                    if not dry_run:
                        rm_fwd_refs(old)
                else:
                    logging.info("Backreferences to this object keyed on foreign field "
                        "{name}: {field} will be not deleted in this migration. "
                        "To add this behavior, re-run with <rm_fwd_refs> "
                        "set to True.".format(name=field,
                                            field=old._fields[field]))
                continue

            # Check for field change
            old_field_obj = old._fields[field]
            new_field_obj = new._fields[field]
            if old_field_obj != new_field_obj:
                if not old_field_obj._required and new_field_obj._required:
                    logging.info("Field {name!r} is now required "
                            "and therefore needs a default value "
                            "for existing records. You can set "
                            "this value in the _migrate() method. "
                            "\nExample: "
                            "\n    if not old.{name}:"
                            "\n        new.{name} = 'default value'"
                            .format(name=field))
                else:
                    logging.info("Old field {name}: {old_field} differs from new field "
                        "{name}: {new_field}. This field will not be "
                        "automatically migrated. If you want to migrate this field, "
                        "you should handle this in your migrate() method.")\
                        .format(name=field, old_field=old_field_obj,
                                new_field=new_field_obj)
                continue

            # Copy values of retained fields
            if not dry_run:
                field_object = cls._fields[field]
                field_object.__set__(
                    new,
                    getattr(old, field),
                    safe=True
                )

        # Copy backreferences
        if not dry_run:
            new.__backrefs = old.__backrefs

        # Run custom migration
        if not dry_run:
            cls._migrate(old, new)

    @classmethod
    def _migrate(cls, old, new):
        """Subclasses can override this class to perform a custom migration.
        This is run after the migrate() method.

        Example:
        ::

            class NewSchema(StoredObject):
                _id = fields.StringField(primary=True, index=True)
                my_string = fields.StringField()

                @classmethod
                def _migrate(cls, old, new):
                    new.my_string = old.my_string + 'yo'

                _meta = {
                    'version_of': OldSchema,
                    'version': 2,
                    'optimistic': True
                }

        :param old: Record from original schema
        :param new: Record from new schema
        """
        return new

    @classmethod
    def explain_migration(cls):
        logging.basicConfig(format='%(levelname)s %(filename)s: %(message)s',
                            level=logging.DEBUG)

        classes = [cls]
        methods = [cls._migrate]
        klass = cls
        while klass._version and klass._version_of:
            classes.insert(0, klass._version_of)
            try:
                methods.insert(0, klass._migrate)
            except AttributeError:
                methods.insert(0, None)
            klass = klass._version_of

        for step in range(len(classes) - 1):

            fr = classes[step]
            to = classes[step + 1]

            logging.info('From schema {0}'.format(fr._name))
            logging.info('\n'.join('\t{0}'.format(field) for field in fr._fields))
            logging.info('')

            logging.info('To schema {0}'.format(to._name))
            logging.info('\n'.join('\t{0}'.format(field) for field in to._fields))
            logging.info('')

            to.migrate(fr, to, verbose=True, dry_run=True)

    @classmethod
    def _must_be_loaded(cls, value):
        if value is not None and not value._is_loaded:
            raise exceptions.DatabaseError('Record must be loaded.')

    @has_storage
    @log_storage
    def _optimistic_insert(self):
        self._primary_key = self._storage[0]._optimistic_insert(
            self._primary_name,
            self.to_storage()
        )

    @has_storage
    @log_storage
    def save(self, force=False):
        """Save a record.

        :param bool force: Save even if no fields have changed; used to update
            back-references
        :returns: List of changed fields

        """
        if self._detached:
            raise exceptions.DatabaseError('Cannot save detached object.')

        for field_name, field_object in self._fields.items():
            if hasattr(field_object, 'on_before_save'):
                field_object.on_before_save(self)

        signals.before_save.send(
            self.__class__,
            instance=self
        )

        cached_data = self._get_cached_data(self._stored_key)
        storage_data = self.to_storage()

        if self._primary_key is not None and cached_data is not None:
            fields_changed = self.get_changed_fields(
                cached_data, storage_data
            )
        else:
            fields_changed = self._fields.keys()

        # Quit if no diffs
        if not fields_changed and not force:
            return []

        # Validate
        for field_name in fields_changed:
            field_object = self._fields[field_name]
            field_object.do_validate(getattr(self, field_name), self)

        primary_changed = (
            self._primary_key != self._stored_key
            and
            self._primary_name in fields_changed
        )

        if self._is_loaded:
            if primary_changed and not getattr(self, '_updating_key', False):
                self.delegate(
                    self._storage[0].remove,
                    False,
                    RawQuery(self._primary_name, 'eq', self._stored_key)
                )
                self._clear_caches(self._stored_key)
                self.insert(self._primary_key, storage_data)
            else:
                self.update_one(self, storage_data=storage_data, saved=True, inmem=True)
        elif self._is_optimistic and self._primary_key is None:
            self._optimistic_insert()
        else:
            self.insert(self._primary_key, storage_data)

        # if primary key has changed, follow back references and update
        # AND
        # run after_save or after_save_on_difference

        if self._is_loaded and primary_changed:
            if not getattr(self, '_updating_key', False):
                self._updating_key = True
                update_backref_keys(self)
                self._stored_key = self._primary_key
                self._updating_key = False
        else:
            self._stored_key = self._primary_key

        self._is_loaded = True

        signals.save.send(
            self.__class__,
            instance=self,
            fields_changed=fields_changed,
            cached_data=cached_data or {},
        )

        self._set_cache(self._primary_key, self)

        return fields_changed

    def reload(self):

        storage_data = self._storage[0].get(self._primary_name, self._storage_key)

        for key, value in storage_data.items():
            field_object = self._fields.get(key, None)
            if isinstance(field_object, Field):
                data_value = storage_data[key]
                if data_value is None:
                    value = None
                else:
                    value = field_object.from_storage(data_value)
                field_object.__set__(self, value, safe=True)
            elif key == '__backrefs':
                self._StoredObject__backrefs = value

        self._stored_key = self._primary_key
        self._set_cache(self._storage_key, self)

    @warn_if_detached
    def __getattr__(self, item):

        errmsg = '{cls} object has no attribute {item}'.format(
            cls=self.__class__.__name__,
            item=item
        )

        if item in self.__backrefs:
            backrefs = []
            for parent, rest0 in self.__backrefs[item].iteritems():
                for field, rest1 in rest0.iteritems():
                    backrefs.extend([
                        (key, parent)
                        for key in rest1
                    ])
            return AbstractForeignList(backrefs)

        # Retrieve back-references
        if '__' in item and not item.startswith('__'):
            item_split = item.split('__')
            if len(item_split) == 2:
                parent_schema_name, backref_key = item_split
                backrefs = deref(self.__backrefs, [backref_key, parent_schema_name], missing={})
                ids = sum(
                    backrefs.values(),
                    []
                )
            elif len(item_split) == 3:
                parent_schema_name, backref_key, parent_field_name = item_split
                ids = deref(self.__backrefs, [backref_key, parent_schema_name, parent_field_name], missing=[])
            else:
                raise AttributeError(errmsg)
            try:
                base_class = self.get_collection(parent_schema_name)
            except KeyError:
                raise exceptions.ModularOdmException(
                    'Unknown schema <{0}>'.format(
                        parent_schema_name
                    )
                )
            return ForeignList(ids, literal=True, base_class=base_class)

        raise AttributeError(errmsg)

    @warn_if_detached
    def __setattr__(self, key, value):
        if key not in self._fields and not key.startswith('_'):
            warnings.warn('Setting an attribute that is neither a field nor a protected value.')
        super(StoredObject, self).__setattr__(key, value)

    # Querying ######

    @classmethod
    def _parse_key_value(cls, value):
        if isinstance(value, StoredObject):
            return value._primary_key, value
        return value, cls.load(cls._pk_to_storage(value))

    @classmethod
    @has_storage
    def _pk_to_storage(cls, key):
        return cls._fields[cls._primary_name].to_storage(key)

    @classmethod
    def _process_query(cls, query):

        if isinstance(query, RawQuery):
            field = cls._fields.get(query.attribute)
            if field is None:
                return
            if field._is_foreign:
                if getattr(query.argument, '_fields', None):
                    if field._is_abstract:
                        query.argument = (
                            query.argument._primary_key,
                            query.argument._name,
                        )
                    else:
                        query.argument = query.argument._primary_key
        elif isinstance(query, QueryGroup):
            for node in query.nodes:
                cls._process_query(node)

    @classmethod
    @has_storage
    @log_storage
    def find(cls, query=None, **kwargs):
        cls._process_query(query)
        return cls._storage[0].QuerySet(
            cls,
            cls._storage[0].find(query, **kwargs)
        )

    @classmethod
    @has_storage
    @log_storage
    def find_one(cls, query=None, **kwargs):
        cls._process_query(query)
        stored_data = cls._storage[0].find_one(query, **kwargs)
        return cls.load(
            key=stored_data[cls._primary_name],
            data=stored_data
        )

    # Queueing

    @classmethod
    def delegate(cls, method, conflict=None, *args, **kwargs):
        """Execute or queue a database action. Variable positional and keyword
        arguments are passed to the provided method.

        :param function method: Method to execute or queue
        :param bool conflict: Potential conflict between cache_sandbox and backend,
            e.g., in the event of bulk updates or removes that bypass the
            cache_sandbox

        """
        if cls.queue.active:
            action = WriteAction(method, *args, **kwargs)
            if conflict:
                logger.warn('Delayed write {0!r} may cause the cache to '
                            'diverge from the database until changes are '
                            'committed.'.format(action))
            cls.queue.push(action)
        else:
            method(*args, **kwargs)

    @classmethod
    def start_queue(cls):
        """Start the queue. Between calling `start_queue` and `commit_queue`,
        all writes will be deferred to the queue.

        """
        cls.queue.start()

    @classmethod
    def clear_queue(cls):
        """Clear the queue.

        """
        cls.queue.clear()

    @classmethod
    def cancel_queue(cls):
        """Cancel any pending actions. This method clears the queue and also
        clears caches if any actions are pending.

        """
        if cls.queue:
            cls._cache.clear()
            cls._object_cache.clear()
        cls.clear_queue()

    @classmethod
    def commit_queue(cls):
        """Commit all queued actions. If any actions fail, clear caches. Note:
        the queue will be cleared whether an error is raised or not.

        """
        try:
            cls.queue.commit()
            cls.clear_queue()
        except:
            cls.cancel_queue()
            raise

    @classmethod
    def subscribe(cls, signal_name, weak=True):
        """

        :param str signal_name: Name of signal to subscribe to; must be found
            in ``signals.py``.
        :param bool weak: Create weak reference to callback
        :returns: Decorator created by ``Signal::connect_via``
        :raises: ValueError if signal is not found

        Example usage: ::

            >>> @Schema.subscribe('before_save')
            ... def listener(cls, instance):
            ...     instance.value += 1

        """
        try:
            signal = getattr(signals, signal_name)
        except AttributeError:
            raise ValueError(
                'Signal {0} not found'.format(signal_name)
            )
        sender = None if cls._is_root else cls
        return signal.connect_via(sender, weak)

    @classmethod
    @has_storage
    def insert(cls, key, val):
        cls.delegate(
            cls._storage[0].insert,
            False,
            cls._primary_name,
            cls._pk_to_storage(key),
            val
        )

    @classmethod
    def _includes_foreign(cls, keys):
        for key in keys:
            if key in cls._fields and cls._fields[key]._is_foreign:
                return True
        return False

    @classmethod
    def _data_to_storage(cls, data):

        storage_data = {}

        for key, value in data.items():
            if key in cls._fields:
                field_object = cls._fields[key]
                if key == cls._primary_name:
                    continue
                storage_data[key] = field_object.to_storage(value)
            else:
                storage_data[key] = value

        return storage_data

    def _update_in_memory(self, storage_data):
        for field_name, data_value in storage_data.items():
            field_object = self._fields[field_name]
            field_object.__set__(self, data_value, safe=True)
        self.save()

    @classmethod
    def _which_to_obj(cls, which):
        if isinstance(which, QueryBase):
            return cls.find_one(which)
        if isinstance(which, StoredObject):
            return which
        return cls.load(cls._pk_to_storage(which))

    @classmethod
    @has_storage
    def update_one(cls, which, data=None, storage_data=None, saved=False, inmem=False):

        storage_data = storage_data or cls._data_to_storage(data)
        includes_foreign = cls._includes_foreign(storage_data.keys())
        obj = cls._which_to_obj(which)

        if saved or not includes_foreign:
            cls.delegate(
                cls._storage[0].update,
                False,
                RawQuery(
                    cls._primary_name, 'eq', obj._primary_key
                ),
                storage_data,
            )
            if obj and not inmem:
                obj._dirty = True
            if not saved:
                cls._clear_caches(obj._storage_key)
        else:
            obj._update_in_memory(storage_data)

    @classmethod
    @has_storage
    def update(cls, query, data=None, storage_data=None):

        storage_data = storage_data or cls._data_to_storage(data)
        includes_foreign = cls._includes_foreign(storage_data.keys())

        objs = cls.find(query)
        keys = objs.get_keys()

        if not includes_foreign:
            cls.delegate(
                cls._storage[0].update,
                True,
                query,
                storage_data
            )
            for key in keys:
                obj = cls._get_cache(key)
                if obj is not None:
                    obj._dirty = True

        else:
            for obj in objs:
                obj._update_in_memory(storage_data)

    @classmethod
    @has_storage
    def remove_one(cls, which, rm=True):
        """Remove an object, along with its references and back-references.
        Remove the object from the cache_sandbox and sets its _detached flag to True.

        :param which: Object selector: Query, StoredObject, or primary key
        :param rm: Remove data from backend

        """
        # Look up object
        obj = cls._which_to_obj(which)

        # Remove references
        rm_fwd_refs(obj)
        rm_back_refs(obj)

        # Remove from cache_sandbox
        cls._clear_caches(obj._storage_key)

        # Remove from backend
        if rm:
            cls.delegate(
                cls._storage[0].remove,
                False,
                RawQuery(obj._primary_name, 'eq', obj._storage_key)
            )

        # Set detached
        obj._detached = True

    @classmethod
    @has_storage
    def remove(cls, query=None):
        """Remove objects by query.

        :param query: Query object

        """
        objs = cls.find(query)

        for obj in objs:
            cls.remove_one(obj, rm=False)

        cls.delegate(
            cls._storage[0].remove,
            False,
            query
        )

def rm_fwd_refs(obj):
    """When removing an object, other objects with references to the current
    object should remove those references. This function identifies objects
    with forward references to the current object, then removes those
    references.

    :param obj: Object to which forward references should be removed

    """
    for stack, key in obj._backrefs_flat:

        # Unpack stack
        backref_key, parent_schema_name, parent_field_name = stack

        # Get parent info
        parent_schema = obj._collections[parent_schema_name]
        parent_key_store = parent_schema._pk_to_storage(key)
        parent_object = parent_schema.load(parent_key_store)
        if parent_object is None:
            continue

        # Remove forward references
        if parent_object._fields[parent_field_name]._list:
            getattr(parent_object, parent_field_name).remove(obj)
        else:
            parent_field_object = parent_object._fields[parent_field_name]
            setattr(parent_object, parent_field_name, parent_field_object._gen_default())

        # Save
        parent_object.save()

def _collect_refs(obj, fields=None):
    """

    """
    refs = []
    fields = fields or []

    for field_name, field_object in obj._fields.items():

        # Skip if not foreign field
        if not field_object._is_foreign:
            continue

        # Skip if value is None
        value = getattr(obj, field_name)
        if value is None:
            continue

        # Skip if not in fields
        if fields and field_name not in fields:
            continue

        field_refs = []

        # Build list of linked objects if ListField, else single field
        if isinstance(field_object, ListField):
            field_refs.extend([v for v in value if v])
            field_instance = field_object._field_instance
        else:
            field_refs.append(value)
            field_instance = field_object

        # Skip if field does not specify back-references
        if not field_instance._backref_field_name:
            continue

        refs.extend([
            {
                'value': ref,
                'field_name': field_name,
                'field_instance': field_instance,
            }
            for ref in field_refs
        ])

    return refs

def rm_back_refs(obj):
    """When removing an object with foreign fields, back-references from
    other objects to the current object should be deleted. This function
    identifies foreign fields of the specified object whose values are not
    None and which specify back-reference keys, then removes back-references
    from linked objects to the specified object.

    :param obj: Object for which back-references should be removed

    """
    for ref in _collect_refs(obj):
        ref['value']._remove_backref(
            ref['field_instance']._backref_field_name,
            obj,
            ref['field_name'],
            strict=False
        )

def ensure_backrefs(obj, fields=None):
    """Ensure that all forward references on the provided object have the
    appropriate backreferences.

    :param StoredObject obj: Database record
    :param list fields: Optional list of field names to check

    """
    for ref in _collect_refs(obj, fields):
        updated = ref['value']._update_backref(
            ref['field_instance']._backref_field_name,
            obj,
            ref['field_name'],
        )
        if updated:
            logging.debug('Updated reference {}:{}:{}:{}:{}'.format(
                obj._name, obj._primary_key, ref['field_name'],
                ref['value']._name, ref['value']._primary_key,
            ))

def update_backref_keys(obj):
    """

    """
    for ref in _collect_refs(obj):
        ref['value']._update_backref(
            ref['field_instance']._backref_field_name,
            obj,
            ref['field_name'],
        )

    for stack, key in obj._backrefs_flat:

        # Unpack stack
        backref_key, parent_schema_name, parent_field_name = stack

        # Get parent info
        parent_schema = obj._collections[parent_schema_name]
        parent_key_store = parent_schema._pk_to_storage(key)
        parent_object = parent_schema.load(parent_key_store)
        if parent_object is None:
            continue

        #
        field_object = parent_object._fields[parent_field_name]
        if field_object._list:
            value = getattr(parent_object, parent_field_name)
            if field_object._is_abstract:
                idx = value.index((obj._stored_key, obj._name))
                value[idx] = (obj._primary_key, obj._name)
            else:
                idx = value.index(obj._stored_key)
                value[idx] = obj
        else:
            setattr(parent_object, parent_field_name, obj)

        # Save
        parent_object.save()
