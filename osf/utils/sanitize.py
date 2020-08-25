from past.builtins import basestring
import json
import collections

import bleach


def is_iterable(obj):
    return isinstance(obj, collections.Iterable)


def is_iterable_but_not_string(obj):
    """Return True if ``obj`` is an iterable object that isn't a string."""
    return (is_iterable(obj) and not hasattr(obj, 'strip'))


def strip_html(unclean, tags=None):
    """Sanitize a string, removing (as opposed to escaping) HTML tags

    :param unclean: A string to be stripped of HTML tags

    :return: stripped string
    :rtype: str
    """
    if isinstance(unclean, bytes):
        unclean = unclean.decode()

    if not tags:
        tags = []

    if unclean is None:
        return u''
    elif isinstance(unclean, dict) or isinstance(unclean, list):
        return bleach.clean(str(unclean), strip=True, tags=[], attributes=[], styles=[])
    # We make this noop for non-string, non-collection inputs so this function can be used with higher-order
    # functions, such as rapply (recursively applies a function to collections)
    # If it's not a string and not an iterable (string, list, dict, return unclean)
    elif not isinstance(unclean, basestring) and not is_iterable(unclean):
        return unclean
    else:
        return bleach.clean(unclean, strip=True, tags=tags, attributes=[], styles=[])


# TODO: Remove unescape_entities when mako html safe comes in
def unescape_entities(value, safe=None):
    """
    Convert HTML-encoded data (stored in the database) to literal characters.

    Intended primarily for endpoints consumed by frameworks that handle their own escaping (eg Knockout)

    :param value: A string, dict, or list
    :param safe: A dict of escape sequences and characters that can be used to extend the set of
        characters that this function will unescape. Use with caution as there are few cases in which
        there will be reason to unescape characters beyond '&'.
    :return: A string or list or dict without html escape characters
    """
    safe_characters = {
        '&amp;': '&',
    }

    if safe and isinstance(safe, dict):
        safe_characters.update(safe)

    if isinstance(value, dict):
        return {
            key: unescape_entities(value, safe=safe_characters)
            for (key, value) in value.items()
        }

    if is_iterable_but_not_string(value):
        return [
            unescape_entities(each, safe=safe_characters)
            for each in value
        ]
    if isinstance(value, basestring):
        for escape_sequence, character in safe_characters.items():
            value = value.replace(escape_sequence, character)
        return value
    return value


def safe_json(value):
    """
    Dump a string to JSON in a manner that can be used for JS strings in mako templates.

    Providing additional forward-slash escaping to prevent injection of closing markup in strings. See:
     http://benalpert.com/2012/08/03/preventing-xss-json.html

    :param value: A string to be converted
    :return: A JSON-formatted string that explicitly escapes forward slashes when needed
    """
    return json.dumps(value).replace('</', '<\\/')  # Fix injection of closing markup in strings


"""
    The following algorithm is based on code from
    https://dev.to/alvaromontoro/building-your-own-color-contrast-checker-4j7o
"""


def is_a11y(value_one, value_two='#FFFFFF', min_ratio=1 / 3):
    """
    Compares two colors and determines if they are above the minimum
    contrast ratio. The default is 1 / 3, which is the contrast ratio for
    large text graphics. See https://color.a11y.com/ for more details.

    :param value_one: a hex formatted color value.
    :param value_two: another hex formatted color value. If none is specified, value_one is
        compared against white (#FFFFFF).
    :param min_ratio: The ratio to compare against. The default is 1 / 3, which is the minimum
        contrast ratio for large text graphics.
    :return: A boolean of whether or not the two colors meet compliance.
    """
    color_rgb_one = hex_to_rgb(value_one)
    color_rgb_two = hex_to_rgb(value_two)

    color_luminance_one = calculate_luminance(color_rgb_one)
    color_luminance_two = calculate_luminance(color_rgb_two)

    if color_luminance_one > color_luminance_two:
        contrast_ratio = ((color_luminance_two + 0.05) / (color_luminance_one + 0.05))
    else:
        contrast_ratio = ((color_luminance_one + 0.05) / (color_luminance_two + 0.05))

    if contrast_ratio < min_ratio:
        return True
    else:
        return False

def hex_to_rgb(value):
    color = value[1:]
    return tuple(int(color[i:i + 2], 16) for i in range(0, 6, 6 // 3))

def calculate_luminance(rgb_color):
    rgb_list = []
    for value in rgb_color:
        value = value / 255
        if value <= 0.03928:
            rgb_list.append(value / 12.92)
        else:
            rgb_list.append(pow((value + 0.055) / 1.055, 2.4))
    return rgb_list[0] * 0.2126 + rgb_list[1] * 0.7152 + rgb_list[2] * 0.0722
