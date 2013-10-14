from modularodm.query.querydialect import DefaultQueryDialect as Q

# Storage backends are attached to models in main; must import
# to get access to data
import main

from framework import app
from website.models import Node
from framework.auth import User
from framework.search.solr import solr

ctx = app.test_request_context()
ctx.push()


def migrate_nodes():
    # Projects
    # our first step is to delete all projects
    solr.delete_all()
    # and then commit that delete
    solr.commit()
    # find all public projects that are not deleted,
    # are public

    for node in Node.find(
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    ):
        node.update_solr()


def migrate_users():
    for user in User.find():
        user.update_solr()


migrate_nodes()
migrate_users()

ctx.pop()
