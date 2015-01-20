PROVIDER_LOOKUP = dict()


def get_service(name):
    """Given a service name, return the provider class"""
    return PROVIDER_LOOKUP[name]()