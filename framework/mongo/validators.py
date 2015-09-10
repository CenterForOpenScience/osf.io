"""
Validators for use in ModularODM
"""
from modularodm.exceptions import ValidationValueError


def string_required(value):
    if value is None or value == '':
        raise ValidationValueError('Value must not be empty.')
