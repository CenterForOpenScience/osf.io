import bleach


#Thank you Lyndsy
def strip_html(unclean):
    """Sanitize a string, removing (as opposed to escaping) HTML tags.
    Note that this will also encode strings with HTML entities
        - e.g.: "This & That" will return "This &amp; That"

    :param unclean: A string to be stripped of HTML tags

    :return: stripped string
    :rtype: str
    """
    return bleach.clean(unclean, strip=True, tags=[], attributes=[], styles=[])


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
