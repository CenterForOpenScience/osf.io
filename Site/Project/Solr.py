import sunburnt
solr = sunburnt.SolrInterface("http://localhost:8983/solr/")


def migrate_solr(args=None):
    # check to see if the document is in the solr database
    if solr.query(id=args['id']).execute():
        db = solr.query(id=args['id']).execute()[0]
        print 'updating...'
        for key, value in args.iteritems():
            # skip over if the key is the same as the add
            if key != 'id':
                # these are multivalued fields,
                # so we have to handle them differently
                if 'tags' in key or 'contributors' in key:
                    if key in db:
                        # for removing tags or contributors
                        if value in db[key]:
                            db[key] = [val for val in db[key] if val != value]
                        # otherwise we can add tags and contributors
                        else:
                            db[key] = db[key] + (value,)
                    # otherwise we just add the key and value
                    else:
                        db[key] = value
                # just add the key and value
                else:
                    db[key] = value
        solr.add(db)
        solr.commit()
    # if its not, just add the arguments
    else:
        solr.add(args)
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


def migrate_user(args=None):
    # if the user is already there, early return
    if solr.query(id=args['id']).execute():
        return
    # otherwise we just add the user
    else:
        solr.add(args)
        solr.commit()


def update_solr(args=None):
    # this is the function we call from
    # when we override the save function
    # since we are overwritting save,
    # we dont have to worry about whats already
    # in the solr db, as we're just going to overwrite it
    if solr.query(id=args['id']).execute():
        db = solr.query(id=args['id']).execute()[0]
        for key, value in args.iteritems():
            db[key] = value
        solr.add(db)
        solr.commit()
    else:
        # if the project is not in the solr, we just
        # add it to solr
        solr.add(args)
        solr.commit()


def delete_solr_doc(args=None):
    print args
    # if the id we have is for a project, then we
    # just deleted the document
    if solr.query(id=args['_id']).execute():
        db = solr.query(id=args['_id']).execute()[0]
        solr.delete(db)
        solr.commit()
        print 'project is now deleted'
    # otherwise we just create a new dictionary while
    # that does not include any reference to the id
    # of our node
    else:
        query = solr.query(id=args['root_id']).execute()[0]
        print query
        update_dict = {}
        for key, value in query.iteritems():
            if args['_id'] not in key:
                update_dict[key] = value
        solr.add(update_dict)
        solr.commit()
