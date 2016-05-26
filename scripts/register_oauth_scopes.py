"""
Register the list of OAuth2 scopes that can be requested by third parties. This populates the Mongo collection
    referenced by CAS when responding to authorization grant requests.

The database class is minimal; the exact specification for what a scope contains lives in the
    python module from which this collection is drawn.
"""
import sys
import logging

from modularodm import Q
from modularodm import storage
from modularodm.exceptions import NoResultsFound

from scripts import utils as script_utils

from framework.auth import oauth_scopes
from framework.mongo import set_up_storage
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.oauth.models import ApiOAuth2Scope

logger = logging.getLogger(__name__)


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
    set_up_storage([ApiOAuth2Scope], storage.MongoStorage)


def do_populate():
    """
    :param dict scope_dict: Given a dictionary of scope definitions, {name: scope_namedtuple}, load the
        resulting data into a database collection
    :return:
    """
    scope_dict = oauth_scopes.public_scopes

    # Clear the scope collection and populate w/ only public scopes,
    # nothing references these objects other than CAS in name only.
    ApiOAuth2Scope.remove()

    for name, scope in scope_dict.iteritems():
        # Update a scope if it exists, else populate
        if scope.is_public is True:
            get_or_create(name, scope.description, save=True)
        else:
            logger.info("{} is not a publicly advertised scope; did not load into database".format(name))


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models

    with TokuTransaction():
        # Set storage backends for this model
        set_backend()
        do_populate()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
