# This dict is built through the metaclass applied to ExternalProvider.
#   It is intentionally empty here, and should remain empty.
PROVIDER_LOOKUP = dict()


def get_service(name):
    """Given a service name, return the provider class"""
    return PROVIDER_LOOKUP[name]()


def serialize_external_account(external_account):
    if external_account is None:
        return None
    return {
        'id': external_account._id,
        'provider_id': external_account.provider_id,
        'display_name': external_account.display_name,
    }