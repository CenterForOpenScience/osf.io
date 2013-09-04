from . import database_source as database
import logging
logging.basicConfig(level=logging.WARNING)

def resolve_parent_backrefs():

    nodes_with_parents = database['node'].find({'_b_node_parent' : {'$ne' : None}})
    for node in nodes_with_parents:
        parent_id = node['_b_node_parent']
        parent_record = database['node'].find_one({'_id' : parent_id})
        if parent_record is None:
            continue
        if node['_id'] not in parent_record['nodes']:
            logging.warn('Deleting backref _b_node_parent from node {nid}'.format(nid=node['_id']))
            database['node'].update(
                {'_id' : node['_id']},
                {'$unset' : {'_b_node_parent' : None}}
            )

def resolve_registration_backrefs():

    nodes_with_registrations = database['node'].find({'_b_node_registrations' : {'$ne' : None}})
    for node in nodes_with_registrations:
        registration_ids = node['_b_node_registrations']
        database['node'].update(
            {'_id' : node['_id']},
            {'$set' : {'registration_list' : registration_ids}}
        )

def resolve_fork_backrefs():

    nodes_with_forks = database['node'].find({'_b_node_forked' : {'$ne' : None}})
    for node in nodes_with_forks:
        fork_ids = node['_b_node_forked']
        database['node'].update(
            {'_id' : node['_id']},
            {'$set' : {'fork_list' : fork_ids}}
        )

def rm_null_child_nodes():

    database['node'].update(
        {'node' : None},
        {'$pull' : {'nodes' : None}},
        multi=True
    )