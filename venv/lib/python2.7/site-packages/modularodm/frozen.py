
import collections

def freeze(value):
    """ Cast value to its frozen counterpart. """
    if isinstance(value, list):
        return FrozenList(*value)
    if isinstance(value, dict):
        return FrozenDict(**value)
    return value

def thaw(value):
    if isinstance(value, FrozenList):
        return value.thaw()
    if isinstance(value, FrozenDict):
        return value.thaw()
    return value

class FrozenDict(collections.Mapping):
    """ Immutable dictionary. """
    def __init__(self, **kwargs):
        self.__data = {key : freeze(value) for key, value in kwargs.items()}

    def thaw(self):
        return {key : thaw(value) for key, value in self.__data.items()}

    def __eq__(self, other):
        if not isinstance(other, FrozenDict):
            return self.thaw() == other
        return super(FrozenDict, self).__eq__(self, other)

    def __getitem__(self, item):
        return self.__data[item]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __repr__(self):
        return repr(self.__data)

class FrozenList(collections.Sequence):
    """ Immutable list. """
    def __init__(self, *args):
        self.__data = [freeze(value) for value in args]

    def thaw(self):
        return [thaw(value) for value in self.__data]

    def __eq__(self, other):
        if not isinstance(other, FrozenList):
            return self.thaw() == other
        return super(FrozenList, self).__eq__(self, other)

    def __getitem__(self, item):
        return self.__data[item]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __repr__(self):
        return repr(self.__data)