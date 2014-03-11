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
    return clean(data).replace('"', '').replace("'", '')


def _deep_clean(data, cleaner=bleach.clean):
    if isinstance(data, dict):
        return {
            key: _deep_clean(value, cleaner)
            for (key, value) in data.iteritems()
        }
    if isinstance(data, list):
        return [
            _deep_clean(value, cleaner)
            for value in data
        ]
    if isinstance(data, basestring):
        return cleaner(data)
    return data


def deep_clean(data, cleaner=bleach.clean, copy=False):
    if copy:
        return _deep_clean(copy.deepcopy(data), cleaner)
    else:
        return _deep_clean(data, cleaner)


def clean(data, cleaner=bleach.clean, copy=False):
    if copy:
        return cleaner(copy.copy(data))
    else:
        return cleaner(data)
