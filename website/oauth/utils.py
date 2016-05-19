from framework.auth.oauth_scopes import public_scopes

# This dict is built through the metaclass applied to ExternalProvider.
#   It is intentionally empty here, and should remain empty.
PROVIDER_LOOKUP = dict()


def get_service(name):
    """Given a service name, return the provider class"""
    return PROVIDER_LOOKUP[name]()

def get_available_scopes():
    return sorted([(name, data.description)
                   for name, data in public_scopes.iteritems()
                   if data.is_public is True])
