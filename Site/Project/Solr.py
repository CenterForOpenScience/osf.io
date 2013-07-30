import sunburnt
import urllib
import urllib2
import ast
solr = sunburnt.SolrInterface("http://localhost:8983/solr/")


def migrate_solr(args=None):
    if solr.query(id=args['id']).execute():
        db = solr.query(id=args['id']).execute()[0]
        for key, value in args.iteritems():
            if 'tags' in key:
                if key in db:
                    if value in db[key]:
                        db[key] = [val for val in db[key] if val != value]
                    else:
                        db[key] = db[key] + (value,)
                else:
                    db[key] = value
            else:
                db[key] = value
        print 'updating...'
        print 'the db is...', db
        solr.add(db)
        solr.commit()
    else:
        print 'adding....'
        solr.add(args)
        solr.commit()


def update_solr(args=None):
    if solr.query(id=args['id']).execute():
        db = solr.query(id=args['id']).execute()[0]
        for key, value in args.iteritems():
            db[key] = value
        print 'updating...'
        print 'the db is...', db
        solr.add(db)
        solr.commit()
    else:
        print 'adding....'
        solr.add(args)
        solr.commit()

def delete_solr_doc(args=None):
    print args
    if solr.query(id=args['_id']).execute():
        db = solr.query(id=args['_id']).execute()[0]
        solr.delete(db)
        solr.commit()
        print 'project is now deleted'
    else:
        query = solr.query(id=args['root_id']).execute()[0]
        print query
        update_dict = {}
        for key, value in query.iteritems():
            if not isinstance(value, bool):
                if args['_id'] not in key and args['_id'] not in value:
                    update_dict[key] = value
        print update_dict
        solr.add(update_dict)
        solr.commit()
        print 'node is now deleted'



