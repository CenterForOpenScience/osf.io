"""
Define a set of scopes to be used by COS Internal OAuth implementation, specifically tailored to work with APIv2.

List of scopes, nomenclature, and rationale can be found in the relevant "Login as OSF- phase 2" proposal document
"""

from collections import namedtuple

from website import settings

# Public scopes are described with 3 pieces of information: list of constituent scopes, a description, and whether or
#   not this scope is available to be requested by the general public

class scope(namedtuple('scope', ['parts_', 'description', 'is_public'])):
    """ Patch to add `ALWAYS_PUBLIC` scope to every selectable scope,
        ensuring that public endpoints are accessible with any token.
    """
    @property
    def parts(self):
        return frozenset((CoreScopes.ALWAYS_PUBLIC, )).union(self.parts_)


class CoreScopes(object):
    """
    The smallest units of permission that can be granted- all other scopes are built out of these.
    Each named constant is a single string."""
    # IMPORTANT: All views should be based on the smallest number of Core scopes required to describe
    # the data in that view

    USERS_READ = 'users_read'
    USERS_WRITE = 'users_write'
    USERS_CREATE = 'users_create'

    USER_EMAIL_READ = 'users.email_read'

    USER_ADDON_READ = 'users.addon_read'

    NODE_BASE_READ = 'nodes.base_read'
    NODE_BASE_WRITE = 'nodes.base_write'

    NODE_CHILDREN_READ = 'nodes.children_read'
    NODE_CHILDREN_WRITE = 'nodes.children_write'

    NODE_FORKS_READ = 'nodes.forks_read'
    NODE_FORKS_WRITE = 'nodes.forks_write'

    NODE_CONTRIBUTORS_READ = 'nodes.contributors_read'
    NODE_CONTRIBUTORS_WRITE = 'nodes.contributors_write'

    NODE_FILE_READ = 'nodes.files_read'
    NODE_FILE_WRITE = 'nodes.files_write'

    NODE_ADDON_READ = 'nodes.addon_read'
    NODE_ADDON_WRITE = 'nodes.addon_write'

    NODE_LINKS_READ = 'nodes.links_read'
    NODE_LINKS_WRITE = 'nodes.links_write'

    NODE_VIEW_ONLY_LINKS_READ = 'node.view_only_links_read'
    NODE_VIEW_ONLY_LINKS_WRITE = 'node.view_only_links_write'

    NODE_PREPRINTS_READ = 'node.preprints_read'
    NODE_PREPRINTS_WRITE = 'node.preprints_write'

    REGISTRATION_VIEW_ONLY_LINKS_READ = 'registration.view_only_links_read'
    REGISTRATION_VIEW_ONLY_LINKS_WRITE = 'registration.view_only_links_write'

    METASCHEMA_READ = 'metaschemas.read'

    NODE_DRAFT_REGISTRATIONS_READ = 'nodes.draft_registrations_read'
    NODE_DRAFT_REGISTRATIONS_WRITE = 'nodes.draft_registrations_write'

    NODE_REGISTRATIONS_READ = 'nodes.registrations_read'
    NODE_REGISTRATIONS_WRITE = 'nodes.registrations_write'

    NODE_CITATIONS_READ = 'nodes.citations_read'
    NODE_CITATIONS_WRITE = 'nodes.citations_write'

    NODE_COMMENTS_READ = 'comments.data_read'
    NODE_COMMENTS_WRITE = 'comments.data_write'

    LICENSE_READ = 'license.data_read'

    COMMENT_REPORTS_READ = 'comments.reports_read'
    COMMENT_REPORTS_WRITE = 'comments.reports_write'

    APPLICATIONS_READ = 'applications_read'
    APPLICATIONS_WRITE = 'applications_write'

    NODE_LOG_READ = 'nodes.logs_read'
    TOKENS_READ = 'tokens_read'
    TOKENS_WRITE = 'tokens_write'

    INSTITUTION_READ = 'institutions_read'

    SEARCH = 'search_read'

    ACTIONS_READ = 'actions_read'
    ACTIONS_WRITE = 'actions_write'

    MODERATORS_READ = 'moderators_read'
    MODERATORS_WRITE = 'moderators_write'

    NODE_REQUESTS_READ = 'node_requests_read'
    NODE_REQUESTS_WRITE = 'node_requests_write'

    PROVIDERS_WRITE = 'providers_write'

    WAFFLE_READ = 'waffle_read'

    NULL = 'null'

    # NOTE: Use with extreme caution.
    # This should NEVER be assigned to endpoints:
    #    - with mutable data,
    #    - that might contain *anything* that could be personally-identifiable,
    #    - as a write scope
    ALWAYS_PUBLIC = 'always_public'

    ORGANIZER_COLLECTIONS_BASE_READ = 'collections.base_read'
    ORGANIZER_COLLECTIONS_BASE_WRITE = 'collections.base_write'

    GUIDS_READ = 'guids.base_read'

    WIKI_BASE_READ = 'wikis.base_read'

    IDENTIFIERS_READ = 'identifiers.data_read'


class ComposedScopes(object):
    """
    Composed scopes, listed in increasing order of access (most restrictive first). Each named constant is a tuple.
    """
    # IMPORTANT: Composed scopes exist only as an internal implementation detail.
    # All views should be based on selections from CoreScopes, above

    # Users collection
    USERS_READ = (CoreScopes.USERS_READ, )
    USERS_WRITE = USERS_READ + (CoreScopes.USERS_WRITE,)
    USERS_CREATE = USERS_READ + (CoreScopes.USERS_CREATE, )

    # User extensions
    USER_EMAIL_READ = (CoreScopes.USER_EMAIL_READ, )

    # Applications collection
    APPLICATIONS_READ = (CoreScopes.APPLICATIONS_READ, )
    APPLICATIONS_WRITE = APPLICATIONS_READ + (CoreScopes.APPLICATIONS_WRITE,)

    # Tokens collection
    TOKENS_READ = (CoreScopes.TOKENS_READ,)
    TOKENS_WRITE = TOKENS_READ + (CoreScopes.TOKENS_WRITE,)

    # Guid redirect view
    GUIDS_READ = (CoreScopes.GUIDS_READ, )

    # Metaschemas collection
    METASCHEMAS_READ = (CoreScopes.METASCHEMA_READ, )

    # Draft registrations
    DRAFT_READ = (CoreScopes.NODE_DRAFT_REGISTRATIONS_READ, )
    DRAFT_WRITE = (CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE, )

    # Identifier views
    IDENTIFIERS_READ = (CoreScopes.IDENTIFIERS_READ, )

    # Comment reports collection
    COMMENT_REPORTS_READ = (CoreScopes.COMMENT_REPORTS_READ,)
    COMMENT_REPORTS_WRITE = COMMENT_REPORTS_READ + (CoreScopes.COMMENT_REPORTS_WRITE,)

    # Nodes collection.
    # Base node data includes node metadata, links, children, and preprints.
    NODE_METADATA_READ = (CoreScopes.NODE_BASE_READ, CoreScopes.NODE_CHILDREN_READ, CoreScopes.NODE_LINKS_READ,
                          CoreScopes.NODE_CITATIONS_READ, CoreScopes.NODE_COMMENTS_READ, CoreScopes.NODE_LOG_READ,
                          CoreScopes.NODE_FORKS_READ, CoreScopes.WIKI_BASE_READ, CoreScopes.LICENSE_READ,
                          CoreScopes.IDENTIFIERS_READ, CoreScopes.NODE_PREPRINTS_READ)
    NODE_METADATA_WRITE = NODE_METADATA_READ + \
                    (CoreScopes.NODE_BASE_WRITE, CoreScopes.NODE_CHILDREN_WRITE, CoreScopes.NODE_LINKS_WRITE,
                     CoreScopes.NODE_CITATIONS_WRITE, CoreScopes.NODE_COMMENTS_WRITE, CoreScopes.NODE_FORKS_WRITE,
                     CoreScopes.NODE_PREPRINTS_WRITE)

    # Organizer Collections collection
    # Using Organizer Collections and the node links they collect. Reads Node Metadata.
    ORGANIZER_READ = (CoreScopes.ORGANIZER_COLLECTIONS_BASE_READ,) + NODE_METADATA_READ
    ORGANIZER_WRITE = ORGANIZER_READ + (CoreScopes.ORGANIZER_COLLECTIONS_BASE_WRITE, CoreScopes.NODE_LINKS_WRITE)

    # Privileges relating to editing content uploaded under that node # TODO: Add wiki etc when implemented
    NODE_DATA_READ = (CoreScopes.NODE_FILE_READ, )
    NODE_DATA_WRITE = NODE_DATA_READ + \
                        (CoreScopes.NODE_FILE_WRITE, )

    # Privileges relating to who can access a node (via contributors or registrations)
    NODE_ACCESS_READ = (CoreScopes.NODE_CONTRIBUTORS_READ, CoreScopes.NODE_REGISTRATIONS_READ,
                        CoreScopes.NODE_VIEW_ONLY_LINKS_READ, CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_READ)
    NODE_ACCESS_WRITE = NODE_ACCESS_READ + \
                            (CoreScopes.NODE_CONTRIBUTORS_WRITE, CoreScopes.NODE_REGISTRATIONS_WRITE,
                             CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE, CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_WRITE)

    # Combine all sets of node permissions into one convenience level
    NODE_ALL_READ = NODE_METADATA_READ + NODE_DATA_READ + NODE_ACCESS_READ
    NODE_ALL_WRITE = NODE_ALL_READ + NODE_METADATA_WRITE + NODE_DATA_WRITE + NODE_ACCESS_WRITE

    # Reviews
    REVIEWS_READ = (CoreScopes.ACTIONS_READ, CoreScopes.MODERATORS_READ)
    REVIEWS_WRITE = (CoreScopes.ACTIONS_WRITE, CoreScopes.MODERATORS_WRITE, CoreScopes.PROVIDERS_WRITE)

    # Full permissions: all routes intended to be exposed to third party API users
    FULL_READ = NODE_ALL_READ + USERS_READ + ORGANIZER_READ + GUIDS_READ + METASCHEMAS_READ + DRAFT_READ + REVIEWS_READ + (CoreScopes.INSTITUTION_READ, CoreScopes.SEARCH, )
    FULL_WRITE = FULL_READ + NODE_ALL_WRITE + USERS_WRITE + ORGANIZER_WRITE + DRAFT_WRITE + REVIEWS_WRITE

    # Admin permissions- includes functionality not intended for third-party use
    ADMIN_LEVEL = FULL_WRITE + APPLICATIONS_WRITE + TOKENS_WRITE + COMMENT_REPORTS_WRITE + USERS_CREATE + REVIEWS_WRITE +\
                    (CoreScopes.USER_EMAIL_READ, CoreScopes.USER_ADDON_READ, CoreScopes.NODE_ADDON_READ, CoreScopes.NODE_ADDON_WRITE, CoreScopes.WAFFLE_READ, )

# List of all publicly documented scopes, mapped to composed scopes defined above.
#   Return as sets to enable fast comparisons of provided scopes vs those required by a given node
# These are the ***only*** scopes that will be recognized from CAS
public_scopes = {
    'osf.full_read': scope(parts_=frozenset(ComposedScopes.FULL_READ),
                           description='View all information associated with this account, including for '
                                       'private projects.',
                           is_public=True),
    'osf.full_write': scope(parts_=frozenset(ComposedScopes.FULL_WRITE),
                            description='View and edit all information associated with this account, including for '
                                        'private projects.',
                            is_public=True),
    'osf.users.profile_read': scope(parts_=frozenset(ComposedScopes.USERS_READ),
                                description='Read your profile data',
                                is_public=True),
    'osf.users.email_read': scope(parts_=frozenset(ComposedScopes.USER_EMAIL_READ),
                                        description='Read your primary email address.',
                                        is_public=True),
}

if settings.DEV_MODE:
    public_scopes.update({
        'osf.users.profile_write': scope(parts_=frozenset(ComposedScopes.USERS_WRITE),
                                     description='Read and edit your profile data',
                                     is_public=True),

        'osf.nodes.metadata_read': scope(parts_=frozenset(ComposedScopes.NODE_METADATA_READ),
                                         description='Read a list of all public and private nodes accessible to this '
                                                     'account, and view associated metadata such as project descriptions '
                                                     'and titles',
                                         is_public=True),
        'osf.nodes.metadata_write': scope(parts_=frozenset(ComposedScopes.NODE_METADATA_WRITE),
                                          description='Read a list of all public and private nodes accessible to this '
                                                      'account, and view and edit associated metadata such as project '
                                                      'descriptions and titles',
                                          is_public=True),

        'osf.nodes.data_read': scope(parts_=frozenset(ComposedScopes.NODE_DATA_READ),
                                     description='List and view files associated with any public or private projects '
                                                 'accessible to this account.',
                                     is_public=True),
        'osf.nodes.data_write': scope(parts_=frozenset(ComposedScopes.NODE_DATA_WRITE),
                                      description='List, view, and update files associated with any public or private '
                                                  'projects accessible to this account.',
                                      is_public=True),

        'osf.nodes.access_read': scope(parts_=frozenset(ComposedScopes.NODE_ACCESS_READ),
                                       description='View the contributors list and any established registrations '
                                                   'associated with public or private projects',
                                       is_public=True),
        'osf.nodes.access_write': scope(parts_=frozenset(ComposedScopes.NODE_ACCESS_WRITE),
                                        description='View and edit the contributors list associated with public or '
                                                    'private projects accessible to this account. Also view and create '
                                                    'registrations.',
                                        is_public=True),  # TODO: Language: Does registrations endpoint allow creation of registrations? Is that planned?

        'osf.nodes.full_read': scope(parts_=frozenset(ComposedScopes.NODE_ALL_READ),
                                    description='View all metadata, files, and access rights associated with all public '
                                                'and private projects accessible to this account.',
                                    is_public=True),
        'osf.nodes.full_write': scope(parts_=frozenset(ComposedScopes.NODE_ALL_WRITE),
                                     description='View and edit all metadata, files, and access rights associated with '
                                                 'all public and private projects accessible to this account.',
                                     is_public=True),

        # Undocumented scopes that can not be requested by third parties (per CAS restriction)
        'osf.users.create': scope(parts_=frozenset(ComposedScopes.USERS_CREATE),
                           description='This permission should only be granted to OSF collaborators. Allows a site to '
                                       'programmatically create new users with this account.',
                           is_public=False),

        'osf.admin': scope(parts_=frozenset(ComposedScopes.ADMIN_LEVEL),
                           description='This permission should only be granted to OSF administrators. Allows a site to '
                                       'create, read, edit, and delete all information associated with this account.',
                           is_public=False),
    })


def normalize_scopes(scopes):
    """
    Given a list of public-facing scope names from a CAS token, return the list of internal scopes

    This is useful for converting a single broad scope name (from CAS) into the small constituent parts
        (as used by views)

    :param list scopes: a list public facing scopes
    """
    all_scopes = set()
    for sc in scopes:
        try:
            scope_tuple = public_scopes[sc]
            all_scopes |= scope_tuple.parts
        except KeyError:
            pass
    return all_scopes


if __name__ == '__main__':
    # Print some data to console, to help audit what views/core scopes map to a given public/composed scope
    # Although represented internally as a set, print as a sorted list for readability.
    from pprint import pprint as pp
    pp({k: sorted(v.parts)
        for k, v in public_scopes.iteritems()})
