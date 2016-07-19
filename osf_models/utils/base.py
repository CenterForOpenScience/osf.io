from bson import ObjectId
from furl import furl
from osf_models.app import ModelsConfig as app_config


def get_object_id():
    return str(ObjectId())

def api_v2_url(path_str,
               params=None,
               base_route=app_config.api_domain,
               base_prefix=app_config.api_base,
               **kwargs):
    """
    Convenience function for APIv2 usage: Concatenates parts of the absolute API url based on arguments provided

    For example: given path_str = '/nodes/abcd3/contributors/' and params {'filter[fullname]': 'bob'},
        this function would return the following on the local staging environment:
        'http://localhost:8000/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob'

    This is NOT a full lookup function. It does not verify that a route actually exists to match the path_str given.
    """
    params = params or {}  # Optional params dict for special-character param names, eg filter[fullname]

    base_url = furl.furl(base_route + base_prefix)

    base_url.path.add([x for x in path_str.split('/') if x] + [''])

    base_url.args.update(params)
    base_url.args.update(kwargs)
    return str(base_url)
