from modularodm.query.querydialect import DefaultQueryDialect as Q

class List(list):

    def __init__(self, value=None, literal=False, **kwargs):

        value = value or []
        self._base_class = kwargs.get('base_class', None)

        if literal:
            super(List, self).__init__(value)
        else:
            super(List, self).__init__()
            self.extend(value)

class BaseForeignList(List):

    def _to_primary_keys(self):
        raise NotImplementedError

    def _from_value(self, value):
        raise NotImplementedError

    def _to_data(self):
        return list(super(BaseForeignList, self).__iter__())

    def __iter__(self):
        if self:
            return (self[idx] for idx in range(len(self)))
        return iter([])

    def __setitem__(self, key, value):
        super(BaseForeignList, self).__setitem__(key, self._from_value(value))

    def insert(self, index, value):
        super(BaseForeignList, self).insert(index, self._from_value(value))

    def append(self, value):
        super(BaseForeignList, self).append(self._from_value(value))

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def remove(self, value):
        super(BaseForeignList, self).remove(self._from_value(value))

class ForeignList(BaseForeignList):

    def _from_value(self, value):
        return self._base_class._to_primary_key(value)

    def _to_primary_keys(self):
        return self._to_data()

    def __reversed__(self):
        return ForeignList(
            super(ForeignList, self).__reversed__(),
            base_class=self._base_class
        )

    def __getitem__(self, item):
        result = super(ForeignList, self).__getitem__(item)
        return self._base_class.load(result)

    def __getslice__(self, i, j):
        result = super(ForeignList, self).__getslice__(i, j)
        return ForeignList(result, base_class=self._base_class)

    def __contains__(self, item):
        keys = self._to_primary_keys()
        if isinstance(item, self._base_class):
            return item._primary_key in keys
        if isinstance(item, self._base_class._primary_type):
            return item in keys
        return False

    def index(self, value, start=None, stop=None):
        start = 0 if start is None else start
        stop = len(self) if stop is None else stop
        keys = self._to_primary_keys()
        if isinstance(value, self._base_class):
            return keys.index(value._primary_key, start, stop)
        if isinstance(value, self._base_class._primary_type):
            return keys.index(value, start, stop)
        raise ValueError('{0} is not in list'.format(value))

    def find(self, query=None):
        combined_query = Q(
            self._base_class._primary_name,
            'in',
            self._to_primary_keys()
        )
        if query is not None:
            combined_query = combined_query & query
        return self._base_class.find(combined_query)

class AbstractForeignList(BaseForeignList):

    def _from_value(self, value):
        if hasattr(value, '_primary_key'):
            return (
                value._primary_key,
                value._name
            )
        return value

    def _to_primary_keys(self):
        return [
            item[0]
            for item in self._to_data()
        ]

    def __reversed__(self):
        return AbstractForeignList(
            super(AbstractForeignList, self).__reversed__()
        )

    def get_foreign_object(self, value):
        from modularodm import StoredObject
        return StoredObject.get_collection(value[1])\
            .load(value[0])

    def __getitem__(self, item):
        result = super(AbstractForeignList, self).__getitem__(item)
        return self.get_foreign_object(result)

    def __getslice__(self, i, j):
        result = super(AbstractForeignList, self).__getslice__(i, j)
        return AbstractForeignList(result)

    def __contains__(self, item):
        keys = self._to_primary_keys()
        if hasattr(item, '_primary_key'):
            return item._primary_key in keys
        elif isinstance(item, tuple):
            return item[0] in keys
        return item in keys

    def index(self, value, start=None, stop=None):
        start = 0 if start is None else start
        stop = len(self) if stop is None else stop
        keys = self._to_primary_keys()
        if hasattr(value, '_primary_key'):
            return keys.index(value._primary_key, start, stop)
        elif isinstance(value, tuple):
            return keys.index(value[0], start, stop)
        else:
            try:
                return keys.index(value, start, stop)
            except ValueError:
                raise ValueError('{0} not in list'.format(value))
