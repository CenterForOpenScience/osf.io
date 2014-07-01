'''
Module for sanatizing any data input.
Please add to me.
'''
import bleach
import copy

#TODO Write tests

#Thank you Lyndsy
def scrub_html(value):
    return bleach.clean(value, strip=True, tags=[], attributes=[], styles=[])


def clean_tag(data):
    return clean(data).replace('"', '&quot;').replace("'", '')


def apply_recursive(data, func):
    if isinstance(data, dict):
        return {
            key: apply_recursive(value, func)
            for (key, value) in data.iteritems()
        }
    if isinstance(data, list):
        return [
            apply_recursive(value, func)
            for value in data
        ]
    if isinstance(data, basestring):
        return func(data)
    return data


def deep_clean(data, cleaner=bleach.clean, copy=False):
    if copy:
        return apply_recursive(copy.deepcopy(data), cleaner)
    else:
        return apply_recursive(data, cleaner)


def clean(data, cleaner=bleach.clean, copy=False):
    if copy:
        return cleaner(copy.copy(data))
    else:
        return cleaner(data)


def ensure_clean(value):
    if value != bleach.clean(value):
        raise ValueError


def deep_ensure_clean(data):
    return apply_recursive(data, ensure_clean)

