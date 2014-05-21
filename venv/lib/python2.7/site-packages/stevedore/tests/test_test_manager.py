from mock import Mock, sentinel
from nose.tools import raises
from stevedore import (ExtensionManager, NamedExtensionManager, HookManager,
                       DriverManager, EnabledExtensionManager)
from stevedore.dispatch import (DispatchExtensionManager,
                                NameDispatchExtensionManager)
from stevedore.extension import Extension


test_extension = Extension('test_extension', None, None, None)
test_extension2 = Extension('another_one', None, None, None)

mock_entry_point = Mock(module_name='test.extension', attrs=['obj'])
a_driver = Extension('test_driver', mock_entry_point, sentinel.driver_plugin,
                     sentinel.driver_obj)


# base ExtensionManager

def test_instance_should_use_supplied_extensions():
    extensions = [test_extension, test_extension2]
    em = ExtensionManager.make_test_instance(extensions)

    assert extensions == em.extensions


def test_instance_should_have_default_namespace():
    em = ExtensionManager.make_test_instance([])

    assert em.namespace


def test_instance_should_use_supplied_namespace():
    namespace = 'testing.1.2.3'
    em = ExtensionManager.make_test_instance([], namespace=namespace)

    assert namespace == em.namespace


def test_extension_name_should_be_listed():
    em = ExtensionManager.make_test_instance([test_extension])

    assert test_extension.name in em.names()


def test_iterator_should_yield_extension():
    em = ExtensionManager.make_test_instance([test_extension])

    assert test_extension == next(iter(em))


def test_manager_should_allow_name_access():
    em = ExtensionManager.make_test_instance([test_extension])

    assert test_extension == em[test_extension.name]


def test_manager_should_call():
    em = ExtensionManager.make_test_instance([test_extension])
    func = Mock()

    em.map(func)

    func.assert_called_once_with(test_extension)


def test_manager_should_call_all():
    em = ExtensionManager.make_test_instance([test_extension2,
                                              test_extension])
    func = Mock()

    em.map(func)

    func.assert_any_call(test_extension2)
    func.assert_any_call(test_extension)


def test_manager_return_values():
    def mapped(ext, *args, **kwds):
        return ext.name

    em = ExtensionManager.make_test_instance([test_extension2,
                                              test_extension])
    results = em.map(mapped)
    assert sorted(results) == ['another_one', 'test_extension']


def test_manager_should_eat_exceptions():
    em = ExtensionManager.make_test_instance([test_extension])

    func = Mock(side_effect=RuntimeError('hard coded error'))

    results = em.map(func, 1, 2, a='A', b='B')
    assert results == []


@raises(RuntimeError)
def test_manager_should_propagate_exceptions():
    em = ExtensionManager.make_test_instance([test_extension],
                                             propagate_map_exceptions=True)
    func = Mock(side_effect=RuntimeError('hard coded error'))

    em.map(func, 1, 2, a='A', b='B')


# NamedExtensionManager

def test_named_manager_should_use_supplied_extensions():
    extensions = [test_extension, test_extension2]
    em = NamedExtensionManager.make_test_instance(extensions)

    assert extensions == em.extensions


def test_named_manager_should_have_default_namespace():
    em = NamedExtensionManager.make_test_instance([])

    assert em.namespace


def test_named_manager_should_use_supplied_namespace():
    namespace = 'testing.1.2.3'
    em = NamedExtensionManager.make_test_instance([], namespace=namespace)

    assert namespace == em.namespace


def test_named_manager_should_populate_names():
    extensions = [test_extension, test_extension2]
    em = NamedExtensionManager.make_test_instance(extensions)

    assert ['test_extension', 'another_one'] == em.names()


# HookManager

def test_hook_manager_should_use_supplied_extensions():
    extensions = [test_extension, test_extension2]
    em = HookManager.make_test_instance(extensions)

    assert extensions == em.extensions


def test_hook_manager_should_be_first_extension_name():
    extensions = [test_extension, test_extension2]
    em = HookManager.make_test_instance(extensions)

    # This will raise KeyError if the names don't match
    assert em[test_extension.name]


def test_hook_manager_should_have_default_namespace():
    em = HookManager.make_test_instance([test_extension])

    assert em.namespace


def test_hook_manager_should_use_supplied_namespace():
    namespace = 'testing.1.2.3'
    em = HookManager.make_test_instance([test_extension], namespace=namespace)

    assert namespace == em.namespace


def test_hook_manager_should_return_named_extensions():
    hook1 = Extension('captain', None, None, None)
    hook2 = Extension('captain', None, None, None)

    em = HookManager.make_test_instance([hook1, hook2])

    assert [hook1, hook2] == em['captain']


# DriverManager

def test_driver_manager_should_use_supplied_extension():
    em = DriverManager.make_test_instance(a_driver)

    assert [a_driver] == em.extensions


def test_driver_manager_should_have_default_namespace():
    em = DriverManager.make_test_instance(a_driver)

    assert em.namespace


def test_driver_manager_should_use_supplied_namespace():
    namespace = 'testing.1.2.3'
    em = DriverManager.make_test_instance(a_driver, namespace=namespace)

    assert namespace == em.namespace


def test_instance_should_use_driver_name():
    em = DriverManager.make_test_instance(a_driver)

    assert ['test_driver'] == em.names()


def test_instance_call():
    def invoke(ext, *args, **kwds):
        return ext.name, args, kwds

    em = DriverManager.make_test_instance(a_driver)
    result = em(invoke, 'a', b='C')

    assert result == ('test_driver', ('a',), {'b': 'C'})


def test_instance_driver_property():
    em = DriverManager.make_test_instance(a_driver)

    assert sentinel.driver_obj == em.driver


# EnabledExtensionManager

def test_enabled_instance_should_use_supplied_extensions():
    extensions = [test_extension, test_extension2]
    em = EnabledExtensionManager.make_test_instance(extensions)

    assert extensions == em.extensions


# DispatchExtensionManager

def test_dispatch_instance_should_use_supplied_extensions():
    extensions = [test_extension, test_extension2]
    em = DispatchExtensionManager.make_test_instance(extensions)

    assert extensions == em.extensions


def test_dispatch_map_should_invoke_filter_for_extensions():
    em = DispatchExtensionManager.make_test_instance([test_extension,
                                                      test_extension2])

    filter_func = Mock(return_value=False)

    args = ('A',)
    kw = {'big': 'Cheese'}

    em.map(filter_func, None, *args, **kw)

    filter_func.assert_any_call(test_extension, *args, **kw)
    filter_func.assert_any_call(test_extension2, *args, **kw)


# NameDispatchExtensionManager

def test_name_dispatch_instance_should_use_supplied_extensions():
    extensions = [test_extension, test_extension2]
    em = NameDispatchExtensionManager.make_test_instance(extensions)

    assert extensions == em.extensions


def test_name_dispatch_instance_should_build_extension_name_map():
    extensions = [test_extension, test_extension2]
    em = NameDispatchExtensionManager.make_test_instance(extensions)

    assert test_extension == em.by_name[test_extension.name]
    assert test_extension2 == em.by_name[test_extension2.name]


def test_named_dispatch_map_should_invoke_filter_for_extensions():
    em = NameDispatchExtensionManager.make_test_instance([test_extension,
                                                          test_extension2])

    func = Mock()

    args = ('A',)
    kw = {'BIGGER': 'Cheese'}

    em.map(['test_extension'], func, *args, **kw)

    func.assert_called_once_with(test_extension, *args, **kw)
