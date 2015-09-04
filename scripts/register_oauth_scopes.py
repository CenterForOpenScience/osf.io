"""
Register the list of OAuth2 scopes that can be requested by third parties. This populates the Mongo collection
    referenced by CAS when responding to authorization grant requests.

The database class is minimal; the exact specification for what a scope contains lives in the
    python module from which this collection is drawn.
"""
from modularodm import Q
from modularodm import storage
from modularodm.exceptions import NoResultsFound

from framework.auth import oauth_scopes
from framework.mongo import set_up_storage
from website.oauth.models import ApiOAuth2Scope


def get_or_create(name, description, save=True):
    """
    Populate or update the database entry, as needed

    :param name:
    :param description:
    :return:
    """
    if name != name.lower():
        raise ValueError('Scope names are case-sensitive, and should always be lower-case.')

    try:
        scope_obj = ApiOAuth2Scope.find_one(Q('name', 'eq', name))
    except NoResultsFound:
        scope_obj = ApiOAuth2Scope(name=name, description=description)
        print "Created new database entry for: ", name
    else:
        scope_obj.description = description
        print "Updating existing database entry for: ", name

    if save is True:
        scope_obj.save()
    return scope_obj


def set_backend():
    """Ensure a storage backend is set up for this model"""
    set_up_storage([ApiOAuth2Scope],
                   storage.MongoStorage)


def main(scope_dict):
    """

    :param dict scope_dict: Given a dictionary of scope definitions, {name: scope_namedtuple}, load the
        resulting data into a database collection
    :return:
    """
    for name, scope in scope_dict.iteritems():
        # Update a scope if it exists, else populate
        if scope.public is True:
            new_scope = get_or_create(name, scope.description, save=True)
        else:
            print "{} is not a publicly advertised scope; did not load into database".format(name)
        # TODO: Add additional logic to delete/deactivate non-public scopes if they are already in the database?

if __name__ == "__main__":
    # Create a database connection, then run program.
    from website.app import init_app
    init_app(set_backends=True, routes=False)

    # Set storage backends for this model
    set_backend()
    main(oauth_scopes.public_scopes)
