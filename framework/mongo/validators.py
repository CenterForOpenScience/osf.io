"""
Validators for use in ModularODM
"""
from modularodm.exceptions import ValidationValueError


def string_required(value):
    if value is None or value == '':
        raise ValidationValueError('Value must not be empty.')
    return True


def choice_in(choices, match_case=True):
    """
    Validate that the option provided is from a restricted set of choices

    Returns a callable that can be used as a validator in ModularODM
    :param choices: An iterable of choices allowed for use
    :param bool match_case: If false, perform case-insensitive comparison (for strings)
    :return:
    """

    if match_case:
        choice_set = set(e.upper() if isinstance(e, basestring) else e
                         for e in choices)
    else:
        choice_set = set(choices)

    def validator(value):
        if match_case is True and isinstance(value, basestring):
            value = value.upper()

        if value in choice_set:
            return True
        else:
            raise ValidationValueError('Value must be one of these options: {}'.format(choices))
    return validator
