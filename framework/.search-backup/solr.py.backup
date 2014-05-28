# -*- coding: utf-8 -*-
import logging
import sunburnt

from website import settings
from .utils import clean_solr_doc


logger = logging.getLogger(__name__)

if settings.USE_SOLR:
    try:
        solr = sunburnt.SolrInterface(settings.SOLR_URI)
    except Exception as e:
        logger.error(e)
        logger.warn("The USE_SOLR setting is enabled but there was a problem "
                    "starting the Solr interface. Is the Solr server running?")
        solr = None
else:
    solr = None


def update_solr(args=None):
    # check to see if the document is in the solr database
    try:
        new = solr.query(id=args['id']).execute()[0]
    except IndexError:
        new = dict()

    if args:
        new.update(clean_solr_doc(args))
    solr.add(new)
    solr.commit()


def migrate_solr_wiki(args=None):
    # migrate wiki function occurs after we migrate
    # projects, so its only relevant for projects and
    # nodes that exist in our database
    if solr.query(id=args['id']).execute():
        db = solr.query(id=args['id']).execute()[0]
        for key, value in args.iteritems():
            if 'wiki' in key:
                db[key] = value
        solr.add(db)
        solr.commit()


def update_user(user):
    # if the user is already there, early return
    solr.add({
        'id': user._id,
        'user': user.fullname,
    })
    solr.commit()


def delete_solr_doc(args=None):
    # if the id we have is for a project, then we
    # just deleted the document
    try:
        db = solr.query(id=args['doc_id']).execute()[0]
        for key in db.keys():
            if key[:len(args['_id'])] == args['_id']:
                del db[key]

        solr.add(db)
        solr.commit()
    except IndexError:
        # Document ID doesn't exist in Solr
        logger.warn('id {} not found in Solr'.format(args['_id']))
