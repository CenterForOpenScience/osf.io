"""Tests for stevedore.extension
"""

import mock

from stevedore import extension

ALL_NAMES = ['e1', 't1', 't2']
WORKING_NAMES = ['t1', 't2']


class FauxExtension(object):
    def __init__(self, *args, **kwds):
        self.args = args
        self.kwds = kwds

    def get_args_and_data(self, data):
        return self.args, self.kwds, data


class BrokenExtension(object):
    def __init__(self, *args, **kwds):
        raise IOError("Did not create")


def test_detect_plugins():
    em = extension.ExtensionManager('stevedore.test.extension')
    names = sorted(em.names())
    assert names == ALL_NAMES


def test_get_by_name():
    em = extension.ExtensionManager('stevedore.test.extension')
    e = em['t1']
    assert e.name == 't1'


def test_get_by_name_missing():
    em = extension.ExtensionManager('stevedore.test.extension')
    try:
        em['t3']
    except KeyError:
        pass
    else:
        assert False, 'Failed to raise KeyError'


def test_load_multiple_times_entry_points():
    # We expect to get the same EntryPoint object because we save them
    # in the cache.
    em1 = extension.ExtensionManager('stevedore.test.extension')
    eps1 = [ext.entry_point for ext in em1]
    em2 = extension.ExtensionManager('stevedore.test.extension')
    eps2 = [ext.entry_point for ext in em2]
    assert eps1[0] is eps2[0]


def test_load_multiple_times_plugins():
    # We expect to get the same plugin object (module or class)
    # because the underlying import machinery will cache the values.
    em1 = extension.ExtensionManager('stevedore.test.extension')
    plugins1 = [ext.plugin for ext in em1]
    em2 = extension.ExtensionManager('stevedore.test.extension')
    plugins2 = [ext.plugin for ext in em2]
    assert plugins1[0] is plugins2[0]


def test_use_cache():
    # If we insert something into the cache of entry points,
    # the manager should not have to call into pkg_resources
    # to find the plugins.
    cache = extension.ExtensionManager.ENTRY_POINT_CACHE
    cache['stevedore.test.faux'] = []
    with mock.patch('pkg_resources.iter_entry_points',
                    side_effect=AssertionError('called iter_entry_points')):
        em = extension.ExtensionManager('stevedore.test.faux')
        names = em.names()
    assert names == []


def test_iterable():
    em = extension.ExtensionManager('stevedore.test.extension')
    names = sorted(e.name for e in em)
    assert names == ALL_NAMES


def test_invoke_on_load():
    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    invoke_args=('a',),
                                    invoke_kwds={'b': 'B'},
                                    )
    assert len(em.extensions) == 2
    for e in em.extensions:
        assert e.obj.args == ('a',)
        assert e.obj.kwds == {'b': 'B'}


def test_map_return_values():
    def mapped(ext, *args, **kwds):
        return ext.name

    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    )
    results = em.map(mapped)
    assert sorted(results) == WORKING_NAMES


def test_map_arguments():
    objs = []

    def mapped(ext, *args, **kwds):
        objs.append((ext, args, kwds))

    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    )
    em.map(mapped, 1, 2, a='A', b='B')
    assert len(objs) == 2
    names = sorted([o[0].name for o in objs])
    assert names == WORKING_NAMES
    for o in objs:
        assert o[1] == (1, 2)
        assert o[2] == {'a': 'A', 'b': 'B'}


def test_map_eats_errors():

    def mapped(ext, *args, **kwds):
        raise RuntimeError('hard coded error')

    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    )
    results = em.map(mapped, 1, 2, a='A', b='B')
    assert results == []


def test_map_propagate_exceptions():

    def mapped(ext, *args, **kwds):
        raise RuntimeError('hard coded error')

    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    propagate_map_exceptions=True
                                    )

    try:
        em.map(mapped, 1, 2, a='A', b='B')
        assert False
    except RuntimeError:
        pass


def test_map_errors_when_no_plugins():

    def mapped(ext, *args, **kwds):
        pass

    em = extension.ExtensionManager('stevedore.test.extension.none',
                                    invoke_on_load=True,
                                    )
    try:
        em.map(mapped, 1, 2, a='A', b='B')
    except RuntimeError as err:
        assert 'No stevedore.test.extension.none extensions found' == str(err)


def test_map_method():
    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    )

    result = em.map_method('get_args_and_data', 42)
    assert set(r[2] for r in result) == set([42])
