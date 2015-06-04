import bleach
import json


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
    return escape_html(data).replace('"', '&quot;').replace("'", '')


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
    if isinstance(data, list):
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
def safe_unescape_html(s):
    """
    Return a string without html escape characters.

    :param s: A string
    :return: A string without html escape characters

    """
    safe_characters = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
    }
    for escape_sequence, character in safe_characters.items():
        s = s.replace(escape_sequence, character)
    return s

def safe_json(s):
    """
    Dump a string to JSON in a manner that can be used for JS strings in mako templates.

    Providing additional forward-slash escaping to prevent injection of closing markup in strings. See:
     http://benalpert.com/2012/08/03/preventing-xss-json.html
    :param s: The text to convert
    :return: A JSON string that explicitly escapes forward slashes when needed
    """
    return json.dumps(s).replace('</', '<\\/')  # Fix injection of closing markup in strings
