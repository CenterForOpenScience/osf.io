from stevedore import dispatch


def check_dispatch(ep, *args, **kwds):
    return ep.name == 't2'


def test_dispatch():

    def invoke(ep, *args, **kwds):
        return (ep.name, args, kwds)

    em = dispatch.DispatchExtensionManager(
        'stevedore.test.extension',
        lambda *args, **kwds: True,
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )
    assert len(em.extensions) == 2
    assert set(em.names()) == set(['t1', 't2'])

    results = em.map(check_dispatch,
                     invoke,
                     'first',
                     named='named value',
                     )
    expected = [('t2', ('first',), {'named': 'named value'})]
    assert results == expected


def test_dispatch_map_method():
    em = dispatch.DispatchExtensionManager(
        'stevedore.test.extension',
        lambda *args, **kwds: True,
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )

    results = em.map_method(check_dispatch, 'get_args_and_data',
                            'first')
    assert results == [(('a',), {'b': 'B'}, 'first')]


def test_name_dispatch():

    def invoke(ep, *args, **kwds):
        return (ep.name, args, kwds)

    em = dispatch.NameDispatchExtensionManager(
        'stevedore.test.extension',
        lambda *args, **kwds: True,
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )
    assert len(em.extensions) == 2
    assert set(em.names()) == set(['t1', 't2'])

    results = em.map(['t2'],
                     invoke,
                     'first',
                     named='named value',
                     )
    expected = [('t2', ('first',), {'named': 'named value'})]
    assert results == expected


def test_name_dispatch_ignore_missing():

    def invoke(ep, *args, **kwds):
        return (ep.name, args, kwds)

    em = dispatch.NameDispatchExtensionManager(
        'stevedore.test.extension',
        lambda *args, **kwds: True,
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )

    results = em.map(['t3', 't1'],
                     invoke,
                     'first',
                     named='named value',
                     )
    expected = [('t1', ('first',), {'named': 'named value'})]
    assert results == expected


def test_name_dispatch_map_method():
    em = dispatch.NameDispatchExtensionManager(
        'stevedore.test.extension',
        lambda *args, **kwds: True,
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )

    results = em.map_method(['t3', 't1'], 'get_args_and_data',
                            'first')
    assert results == [(('a',), {'b': 'B'}, 'first')]
