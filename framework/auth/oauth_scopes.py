"""
Define a set of scopes to be used by COS Internal OAuth implementation, specifically tailored to work with APIv2

See https://brandur.org/oauth-scope for discussion of various scope nomenclature systems.

General philosophy:
- Scopes are defined as strings (which external users request). Internal units of scope are referred
    to via named constants. (so internal refactoring can be done without exposing all scopes publicly)
- We divide between two levels of access: read (GET, OPTIONS) and write (everything else)
    - Write access inherently includes read permissions
- Only a few scopes will be advertised publicly. More may be added.
- Do not advertise broad scopes too readily. It is easier to add privileges than to take them away.


Nomenclature scheme:
- All OSF scopes names exposed publicly are prefixed with `osf.`, so that scope names will be unique across
    all COS service APIs that may be offered in the future. (all COS services go through the same SSO system)
- Each APIv2 endpoint is referred to as a single collection name.
- Some endpoints also have subcollections (nodes.files, nodes.contributors)
- If there are subcollections, then group permissions into related categories of behavior and name by behavior instead
    of subcollection (nodes.access)
- It is acceptable to use the same read permission for both the list and detail view of a collection.
- Specific permissions (read, write) are appended to the collection name using '+'. Write permission inherently
    include read permissions.

Usage
- All API endpoints must refer to the very specific, smallest possible units of scope used to access that endpoint
- All public-facing scopes must be defined in terms of these smallest units
- Any public facing scope will be automatically normalized into the smallest units each time a user makes a request.
"""

# TODO: This script may be refactored into a database-population script in the future

class CoreScopes(object):
    """
    The smallest units of permission that can be granted- all other scopes are built out of these.
    Each named constant is a single string."""
    USERS_READ = 'users+read'
    USERS_WRITE = 'users+write'

    NODE_BASE_READ = 'nodes.basic+read'
    NODE_BASE_WRITE = 'nodes.basic+write'

    NODE_CHILDREN_READ = 'nodes.children+read'
    NODE_CHILDREN_WRITE = 'nodes.children.write'

    NODE_CONTRIBUTORS_READ = 'nodes.contributors+read'
    NODE_CONTRIBUTORS_WRITE = 'nodes.contributors+write'

    NODE_FILE_READ = 'nodes.files+read'
    NODE_FILE_WRITE = 'nodes.files+write'

    NODE_LINKS_READ = 'nodes.links+read'
    NODE_LINKS_WRITE = 'nodes.links+write'

    NODE_REGISTRATIONS_READ = 'nodes.registrations+read'
    NODE_REGISTRATIONS_WRITE = 'nodes.registrations+write'

    APPLICATIONS_READ = 'applications+read'
    APPLICATIONS_WRITE = 'applications+write'


class ComposedScopes(object):
    """
    Composed scopes, listed in increasing order of access (most restrictive first). Each named constant is a tuple.
    """

    # Users collection
    USERS_READ = (CoreScopes.USERS_READ,)
    USERS_WRITE = USERS_READ + (CoreScopes.USERS_WRITE,)

    # Applications collection
    APPLICATIONS_READ = (CoreScopes.APPLICATIONS_READ,)
    APPLICATIONS_WRITE = APPLICATIONS_READ + (CoreScopes.APPLICATIONS_WRITE,)

    # Nodes collection.
    # Base node data includes node metadata, links, and children.
    NODE_BASIC_READ = (CoreScopes.NODE_BASE_READ, CoreScopes.NODE_CHILDREN_READ, CoreScopes.NODE_LINKS_READ)
    NODE_BASIC_WRITE = NODE_BASIC_READ + \
                    (CoreScopes.NODE_BASE_WRITE, CoreScopes.NODE_CHILDREN_WRITE, CoreScopes.NODE_LINKS_WRITE)

    # Privileges relating to editing content uploaded under that node # TODO: Add wiki etc when implemented
    NODE_EDITOR_READ = (CoreScopes.NODE_FILE_READ,)
    NODE_EDITOR_WRITE = NODE_EDITOR_READ + \
                        (CoreScopes.NODE_FILE_WRITE,)

    # Privileges relating to who can access a node (via contributors or registrations)
    NODE_ACCESS_READ = (CoreScopes.NODE_CONTRIBUTORS_READ, CoreScopes.NODE_REGISTRATIONS_READ)
    NODE_ACCESS_WRITE = NODE_ACCESS_READ + \
                            (CoreScopes.NODE_CONTRIBUTORS_WRITE, CoreScopes.NODE_REGISTRATIONS_WRITE)

    # Combine all sets of node permissions into one convenience level
    NODE_ALL_READ = NODE_BASIC_READ + NODE_EDITOR_READ + NODE_ACCESS_READ
    NODE_ALL_WRITE = NODE_ALL_READ + NODE_BASIC_WRITE + NODE_EDITOR_WRITE + NODE_ACCESS_WRITE

    # Full permissions: all routes intended to be exposed to third party API users
    FULL_READ = NODE_ALL_READ + USERS_READ
    FULL_WRITE = NODE_ALL_WRITE + USERS_WRITE

    # Admin permissions- includes functionality not intended for third-party use
    ADMIN_LEVEL = FULL_WRITE + APPLICATIONS_WRITE


# List of all publicly documented scopes, mapped to composed scopes defined above.
#   Return as sets to enable fast comparisons of provided scopes vs those required by a given node
# These are the ***only*** scopes that will be recognized from CAS
public_scopes = {  # TODO: Move (most of) this list to a database
    'osf.users+read': frozenset(ComposedScopes.USERS_READ),  # Read profile / user data
    'osf.users+write': frozenset(ComposedScopes.USERS_WRITE),  # Edit profile data

    'osf.nodes.basic+read': frozenset(ComposedScopes.NODE_BASIC_READ),  # Read only access to basic node metadata
    'osf.nodes.basic+write': frozenset(ComposedScopes.NODE_BASIC_WRITE),

    'osf.nodes.editor+read': frozenset(ComposedScopes.NODE_EDITOR_READ),
    'osf.nodes.editor+write': frozenset(ComposedScopes.NODE_EDITOR_WRITE),

    'osf.nodes.access+read': frozenset(ComposedScopes.NODE_ACCESS_READ),
    'osf.nodes.access+write': frozenset(ComposedScopes.NODE_ACCESS_WRITE),

    'osf.nodes.all+read': frozenset(ComposedScopes.NODE_ALL_READ),  # Read-only access to all node & subcollection data
    'osf.nodes.all+write': frozenset(ComposedScopes.NODE_ALL_WRITE),

    'osf.full+read': frozenset(ComposedScopes.FULL_READ),  # Read (but don't edit) all data available to this user (nodes + users)
    'osf.full+write': frozenset(ComposedScopes.FULL_WRITE),

    # Undocumented scopes that can not be requested by third parties (per CAS restriction)
    'osf.admin': frozenset([ComposedScopes.APPLICATIONS_WRITE]),
}
