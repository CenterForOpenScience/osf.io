# -*- coding: utf-8 -*-
import bleach


#Thank you Lyndsy
def strip_html(unclean):
    """Sanitize a string, removing (as opposed to escaping) HTML tags

    :param unclean: A string to be stripped of HTML tags

    :return: stripped string
    :rtype: str
    """
    return bleach.clean(unclean, strip=True, tags=[], attributes=[], styles=[])


def clean_tag(data):
    """Format as a valid Tag

    :param data: A string to be cleaned

    :return: cleaned string
    :rtype: str
    """
    #TODO: make this a method of Tag?
    return escape_html(data).replace('"', '&quot;').replace("'", '&#39')

def is_iterable_but_not_string(obj):
    """Return True if ``obj`` is an iterable object that isn't a string."""
    return (hasattr(obj, '__iter__') and not hasattr(obj, 'strip'))

def escape_html(data):
    """Escape HTML characters in data.

    :param data: A string, dict, or list to clean of HTML characters

    :return: A cleaned object
    :rtype: str or list or dict
    """
    if isinstance(data, dict):
        return {
            key: escape_html(value)
            for (key, value) in data.iteritems()
        }
    if is_iterable_but_not_string(data):
        return [
            escape_html(value)
            for value in data
        ]
    if isinstance(data, basestring):
        return bleach.clean(data)
    return data


def assert_clean(data):
    """Ensure that data is cleaned

    :raise: AssertionError
    """
    def _ensure_clean(value):
        if value != bleach.clean(value):
            raise ValueError

    return escape_html(data)


# TODO: Remove safe_unescape_html when mako html safe comes in
def safe_unescape_html(value):
    """
    Return data without html escape characters.

    :param s: A string, dict, or list
    :return: A string or list or dict without html escape characters

    """
    safe_characters = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
    }
    if isinstance(value, dict):
        return {
            key: safe_unescape_html(value)
            for (key, value) in value.iteritems()
        }

    if is_iterable_but_not_string(value):
        return [
            safe_unescape_html(each)
            for each in value
        ]
    if isinstance(value, basestring):
        for escape_sequence, character in safe_characters.items():
            value = value.replace(escape_sequence, character)
        return value
    return value
