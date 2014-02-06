"""
Enable the wiki and files add-ons for all existing nodes.
"""

from website.app import init_app
from website import models

app = init_app('website.settings', set_backends=True, routes=True)

node_mongo = models.Node._storage[0].store

def nodes_to_abstract():

    for node in node_mongo.find():
        if node['nodes']:
            if isinstance(node['nodes'][0], basestring):
                abstract = [
                    [each, 'node']
                    for each in node['nodes']
                ]
                print node['_id'], abstract

if __name__ == '__main__':
    nodes_to_abstract()
