"""
Register the list of OAuth2 scopes that can be requested by third parties. This populates the Postgres collection
referenced by CAS when responding to authorization grant requests. The database class is minimal; the exact
specification for what a scope contains lives in the python module from which this collection is drawn.
"""

import sys
import logging

import django
from django.db import transaction

django.setup()

from scripts import utils as script_utils

from framework.auth import oauth_scopes
from osf.models import ApiOAuth2Scope
from website.app import init_app


logger = logging.getLogger(__name__)


def get_or_create(name, description, save=True):
    """
    Populate or update the database entry, as needed

    :param name: the name of the scope
    :param description: the description of the scope
    :return: the scope object
    """

    if name != name.lower():
        raise ValueError('Scope names are case-sensitive, and should always be lower-case.')

    try:
        scope_obj = ApiOAuth2Scope.objects.get(name=name)
        setattr(scope_obj, 'description', description)
        print("Updating existing database entry for: %s", name)
    except ApiOAuth2Scope.DoesNotExist:
        scope_obj = ApiOAuth2Scope(name=name, description=description)
        print("Created new database entry for: %s", name)

    if save:
        scope_obj.save()

    return scope_obj


def do_populate(clear=False):
    """
    Given a dictionary of scope definitions, {name: scope_namedtuple}, load the
    resulting data into a database collection
    """

    scope_dict = oauth_scopes.public_scopes

    if clear:
        ApiOAuth2Scope.remove()

    for name, scope in scope_dict.iteritems():
        # Update a scope if it exists, else populate
        if scope.is_public is True:
            get_or_create(name, scope.description, save=True)
        else:
            logger.info("{} is not a publicly advertised scope; did not load into database".format(name))


def main(dry=True):

    init_app(routes=False)
    with transaction.atomic():
        do_populate(clear=True)
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
