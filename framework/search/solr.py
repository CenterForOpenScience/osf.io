import sunburnt
from website import settings

if settings.use_solr:
    solr = sunburnt.SolrInterface("http://localhost:8983/solr/")


def update_solr(args=None):
    # check to see if the document is in the solr database

    try:
        new = solr.query(id=args['id']).execute()[0]
    except IndexError:
        new = dict()

    new.update(args)
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
    print 'deleting.'
    try:
        db = solr.query(id=args['doc_id']).execute()[0]
        for key in db.keys():
            print key
            if key[:len(args['_id'])] == args['_id']:
                print 'deleting'
                del db[key]

        solr.add(db)
        solr.commit()
    except IndexError:
        # Document ID doesn't exist in Solr
        print 'id {} not found in Solr'.format(args['_id'])
