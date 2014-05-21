"""Tests for stevedore.exmaple.simple
"""

from stevedore.example import simple


def test_simple_items():
    f = simple.Simple(100)
    text = ''.join(f.format({'a': 'A', 'b': 'B'}))
    expected = '\n'.join([
        'a = A',
        'b = B',
        '',
    ])
    assert text == expected
