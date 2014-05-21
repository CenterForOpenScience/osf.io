from stevedore import hook


def test_hook():
    em = hook.HookManager(
        'stevedore.test.extension',
        't1',
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )
    assert len(em.extensions) == 1
    assert em.names() == ['t1']


def test_get_by_name():
    em = hook.HookManager(
        'stevedore.test.extension',
        't1',
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )
    e_list = em['t1']
    assert len(e_list) == 1
    e = e_list[0]
    assert e.name == 't1'


def test_get_by_name_missing():
    em = hook.HookManager(
        'stevedore.test.extension',
        't1',
        invoke_on_load=True,
        invoke_args=('a',),
        invoke_kwds={'b': 'B'},
    )
    try:
        em['t2']
    except KeyError:
        pass
    else:
        assert False, 'Failed to raise KeyError'
