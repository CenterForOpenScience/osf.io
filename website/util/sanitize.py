# -*- coding: utf-8 -*-
import bleach

from osf.utils.sanitize import is_iterable_but_not_string


def escape_html(data):
    """Escape HTML characters in data (as opposed to stripping them out entirely). Will ignore whitelisted tags.

    :param data: A string, dict, or list to clean of HTML characters

    :return: A cleaned object
    :rtype: str or list or dict
    """
    if isinstance(data, dict):
        return {
            key: escape_html(value)
            for (key, value) in data.items()
        }
    if is_iterable_but_not_string(data):
        return [
            escape_html(value)
            for value in data
        ]
    if isinstance(data, str):
        return bleach.clean(data)
    return data


def temp_ampersand_fixer(s):
    """As a workaround for ampersands stored as escape sequences in database, unescape text before use on a safe page

    Explicitly differentiate from safe_unescape_html in case use cases/behaviors diverge
    """
    return s.replace('&amp;', '&')
