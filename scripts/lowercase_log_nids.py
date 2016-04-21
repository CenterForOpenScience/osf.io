import sys

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

from website.app import init_app


def lowercase_nids():
    for log in db.nodelog.find({'$or': [
        {'params.node': {'$regex': '[A-Z]'}},
        {'params.project': {'$regex': '[A-Z]'}},
        {'params.registration': {'$regex': '[A-Z]'}},
        {'__backrefs.logged.node.logs': {'$regex': '[A-Z]'}},
    ]}):
        update = {}
        if log.get('__backrefs', {}).get('logged', {}).get('node', {}).get('logs'):
            update['__backrefs.logged.node.logs'] = [nid.lower() for nid in log['__backrefs']['logged']['node']['logs']]
        if log['params'].get('node'):
            update['params.node'] = log['params']['node'].lower()
        if log['params'].get('project'):
            update['params.project'] = log['params']['project'].lower()
        if log['params'].get('registration'):
            update['params.registration'] = log['params']['registration'].lower()
        db.nodelog.update({'_id': log['_id']}, {'$set': update})

    assert db.nodelog.find({'$or': [
        {'params.node': {'$regex': '[A-Z]'}},
        {'params.project': {'$regex': '[A-Z]'}},
        {'params.registration': {'$regex': '[A-Z]'}},
        {'__backrefs.logged.node.logs': {'$regex': '[A-Z]'}},
    ]}).count() == 0


def main():
    init_app(routes=False)
    dry_run = '--dry' in sys.argv
    with TokuTransaction():
        lowercase_nids()
        if dry_run:
            raise Exception('Dry run')


if __name__ == '__main__':
    main()
