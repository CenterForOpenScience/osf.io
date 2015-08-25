# -*- coding: utf-8 -*-
import bleach
import json


def strip_html(unclean):
    """Sanitize a string, removing (as opposed to escaping) HTML tags

    :param unclean: A string to be stripped of HTML tags

    :return: stripped string
    :rtype: str
    """
    return bleach.clean(unclean, strip=True, tags=[], attributes=[], styles=[])


# TODO: Not used anywhere except unit tests? Review for deletion
def clean_tag(data):
    """Format as a valid Tag

    :param data: A string to be cleaned

    :return: cleaned string
    :rtype: str
    """
    # TODO: make this a method of Tag?
    return escape_html(data).replace('"', '&quot;').replace("'", '&#39')


def is_iterable_but_not_string(obj):
    """Return True if ``obj`` is an iterable object that isn't a string."""
    return (hasattr(obj, '__iter__') and not hasattr(obj, 'strip'))


def escape_html(data):
    """Escape HTML characters in data (as opposed to stripping them out entirely). Will ignore whitelisted tags.

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


# FIXME: Not sure what this function is trying to accomplish. Candidate for deletion?
def assert_clean(data):
    """Ensure that data is cleaned

    :raise: AssertionError
    """
    def _ensure_clean(value):
        if value != bleach.clean(value):
            raise ValueError

    return escape_html(data)


# TODO: Remove unescape_entities when mako html safe comes in
def unescape_entities(value):
    """
    Convert HTML-encoded data (stored in the database) to literal characters.

    Intended primarily for endpoints consumed by frameworks that handle their own escaping (eg Knockout)

    :param value: A string, dict, or list
    :return: A string or list or dict without html escape characters
    """
    safe_characters = {
        '&amp;': '&',
    }

    if isinstance(value, dict):
        return {
            key: unescape_entities(value)
            for (key, value) in value.iteritems()
        }

    if is_iterable_but_not_string(value):
        return [
            unescape_entities(each)
            for each in value
        ]
    if isinstance(value, basestring):
        for escape_sequence, character in safe_characters.items():
            value = value.replace(escape_sequence, character)
        return value
    return value


def temp_ampersand_fixer(s):
    """As a workaround for ampersands stored as escape sequences in database, unescape text before use on a safe page

    Explicitly differentiate from safe_unescape_html in case use cases/behaviors diverge
    """
    return s.replace('&amp;', '&')


def safe_json(value):
    """
    Dump a string to JSON in a manner that can be used for JS strings in mako templates.

    Providing additional forward-slash escaping to prevent injection of closing markup in strings. See:
     http://benalpert.com/2012/08/03/preventing-xss-json.html

    :param value: A string to be converted
    :return: A JSON-formatted string that explicitly escapes forward slashes when needed
    """
    return json.dumps(value).replace('</', '<\\/')  # Fix injection of closing markup in strings
