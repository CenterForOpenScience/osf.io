# -*- coding: utf-8 -*-

import weakref


# TODO: Test me @jmcarp
class CallbackField(object):

    def __init__(self, default, callback):
        self.data = weakref.WeakKeyDictionary()
        self.default = default
        self.callback = callback

    def __get__(self, instance, owner):
        try:
            return self.data[instance]
        except KeyError:
            return self.default

    def __set__(self, instance, value):
        current = self.__get__(instance, None)
        self.data[instance] = value
        self.callback(instance, value, current)


def set_dirty_factory(field='_dirty'):
    def set_dirty(instance, new, current):
        if new != current:
            setattr(instance, field, True)
    return set_dirty


class DirtyField(CallbackField):

    def __init__(self, default, field='_dirty'):
        super(DirtyField, self).__init__(default, set_dirty_factory(field))
