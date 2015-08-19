"""
Define a set of scopes to be used by COS Internal OAuth implementation
"""

class CoreScopes(object):
    """The smallest units of permission that can be granted- all other scopes are built out of these"""
    NODE_FILE_READ = 'nodes.files.read'
    NODE_FILE_WRITE = 'nodes.files.write'

    APPLICATIONS_READ = 'applications.read'
    APPLICATIONS_EDIT = 'applications.write'


class ComposedScopes(object):
    """
    Composed scopes, listed in increasing order of access (most restrictive first).

    Naming scheme:
    - collection : Read + write access to a given collection
    - collection.subcollection : Read + write access to one given subcollection

    - collection+read / collection+write : the specified permission type applied to a given collection

    - (special/reserved names) Full, profile etc: convenience names for certain combinations of permissions

    - collection.read / collection.write : power over collection and

    Some """
    # Node collection
    NODE_ALL = []
    NODE_READ = []
    NODE_WRITE = []

    # Node.files subcollection

    # Node.wiki subcollection

    # User collection

    # Applications collection
    APPLICATIONS_READ = [CoreScopes.APPLICATIONS_READ]
    APPLICATIONS_WRITE = APPLICATIONS_READ + [CoreScopes.APPLICATIONS_EDIT]


# List of all publicly documented scopes, mapped to granular or compound scope elements above
public_scopes = {}
