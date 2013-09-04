
import collections
import logging
logging.basicConfig(level=logging.WARNING)

from bson import ObjectId

from . import database_source as database
# from pymongo import MongoClient
# database = MongoClient('mongodb://localhost:20771')['osf20120530']

def get_initial_logs():

    nodes = database['node'].find({
            'forked_from' : None,
            'registered_from' : None,
        }, 
        {'logs' : True}
    )

    logs = [
        node['logs'][0] for node in nodes
        if 'logs' in node and node['logs']
    ]

    return logs

def get_duplicate_logs(logs):
    
    counter = collections.Counter(logs)
    duplicate_logs = [log for log, count in counter.items() if count > 1]
    return duplicate_logs

def node_in_parent_nodes(node):

    if '_b_node_parent' in node:
        parent = database['node'].find_one(node['_b_node_parent'])
        return node['_id'] in parent['nodes']
    
    return False

def node_is_child_parent(node):

    if node['nodes']:
        child0 = database['node'].find_one(node['nodes'][0])
        child0_parent = child0.get('_b_node_parent')
        if child0_parent:
            return node['_id'] == child0_parent

    return False

def node_in_initial_log(log_id, node):

    log = database['nodelog'].find_one(ObjectId(log_id))
    if not log:
        return False

    params = log.get('params')
    if not params:
        return False

    action = log.get('action')
    if action == 'project_created':
        params_node = params.get('project')
    elif action == 'node_created':
        params_node = params.get('node')
    
    if not params_node:
        return False

    return params_node == node['_id']

def resolve_conflict(log, dry_run=False, force=False):
    
    nodes = database['node'].find({
        'logs.0' : log,
        'is_fork' : False,
        'is_registration' : False,
    })
    nodes = list(nodes)

    for idx in range(len(nodes)):
        node = nodes[idx]
        node['_node_in_parent_nodes'] = node_in_parent_nodes(node)
        node['_node_is_child_parent'] = node_is_child_parent(node)
        node['_node_in_initial_log'] = node_in_initial_log(log, node)

    ordered_nodes = sorted(
        nodes, 
        key=lambda node: (
            len(node['logs']),
            node['_node_in_parent_nodes'],
            node['_node_is_child_parent'],
            node['_node_in_initial_log'],
        )
    )
    
    for node in ordered_nodes[:-1]:
        logging.warn(
            'Deleting node {title} ({id})'.format(
                title=node['title'],
                id=node['_id'],
            )
        )
        diff = set(node['logs']) - set(ordered_nodes[-1]['logs'])
        tied = (
            len(node['logs']) == len(ordered_nodes[-1]['logs'])
            and node['_node_in_parent_nodes'] == ordered_nodes[-1]['_node_in_parent_nodes']
            and node['_node_is_child_parent'] == ordered_nodes[-1]['_node_is_child_parent']
            and node['_node_in_initial_log'] == ordered_nodes[-1]['_node_in_initial_log']
        )
        if diff or tied:
            logging.warn('\nWARNING: Node to be deleted is ahead of current node.')
            if force:
                logging.warn('Deleting node anyway.\n')
                if not dry_run:
                    database['node'].remove({'_id' : node['_id']})
        elif not dry_run:
            database['node'].remove({'_id' : node['_id']})

def clean(dry_run=False, force=False):
    
    duplicate_logs = get_duplicate_logs(get_initial_logs())
    for log in duplicate_logs:
        resolve_conflict(log, dry_run=dry_run, force=force)
