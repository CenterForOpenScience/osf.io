import collections
from bson import ObjectId
import bleach

def generate_object_id():
    return str(ObjectId())


def strip_html(unclean):
    """Sanitize a string, removing (as opposed to escaping) HTML tags

    :param unclean: A string to be stripped of HTML tags

    :return: stripped string
    :rtype: str
    """
    # We make this noop for non-string, non-collection inputs so this function can be used with higher-order
    # functions, such as rapply (recursively applies a function to collections)
    if not isinstance(unclean, basestring) and not is_iterable(unclean) and unclean is not None:
        return unclean
    return bleach.clean(unclean, strip=True, tags=[], attributes=[], styles=[])


def is_iterable(obj):
    return isinstance(obj, collections.Iterable)
