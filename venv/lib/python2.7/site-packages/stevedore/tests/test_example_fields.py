"""Tests for stevedore.exmaple.fields
"""

from stevedore.example import fields


def test_simple_items():
    f = fields.FieldList(100)
    text = ''.join(f.format({'a': 'A', 'b': 'B'}))
    expected = '\n'.join([
        ': a : A',
        ': b : B',
        '',
    ])
    assert text == expected


def test_long_item():
    f = fields.FieldList(25)
    text = ''.join(f.format({'name': 'a value longer than the allowed width'}))
    expected = '\n'.join([
        ': name : a value longer',
        '    than the allowed',
        '    width',
        '',
    ])
    assert text == expected
