from framework.auth.oauth_scopes import public_scopes

# This dict is built through the metaclass applied to ExternalProvider.
#   It is intentionally empty here, and should remain empty.
PROVIDER_LOOKUP = dict()


def get_service(name):
    """Given a service name, return the provider class"""
    return PROVIDER_LOOKUP[name]()

def get_available_scopes():
    scopes = [(scope_key, public_scopes[scope_key].description) for scope_key in public_scopes if public_scopes[scope_key].is_public]
    scopes.sort()
    return scopes
