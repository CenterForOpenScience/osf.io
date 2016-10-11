import collections
from bson import ObjectId
import furl
from osf.apps import AppConfig as app_config
import bleach

def generate_object_id():
    return str(ObjectId())

def api_v2_url(path_str,
               params=None,
               base_route=app_config.api_domain,
               base_prefix=app_config.api_base,
               **kwargs):
    """
    Convenience function for APIv2 usage: Concatenates parts of the
    absolute API url based on arguments provided

    For example: given path_str = '/nodes/abcd3/contributors/' and params {'filter[fullname]': 'bob'},
        this function would return the following on the local staging environment:
        'http://localhost:8000/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob'

    This is NOT a full lookup function. It does not verify that a route actually
    exists to match the path_str given.
    """
    params = params or {}  # Optional params dict for special-character param names, eg filter[fullname]

    base_url = furl.furl(base_route + base_prefix)

    base_url.path.add([x for x in path_str.split('/') if x] + [''])

    base_url.args.update(params)
    base_url.args.update(kwargs)
    return str(base_url)


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
