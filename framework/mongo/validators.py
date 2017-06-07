"""
Validators for use in ModularODM
"""
from modularodm.exceptions import ValidationValueError


def string_required(value):
    if value is None or value.strip() == '':
        raise ValidationValueError('Value must not be empty.')
    return True
