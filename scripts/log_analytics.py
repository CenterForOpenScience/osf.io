from __future__ import print_function, absolute_import

import time
import sys
import argparse
from faker import Faker
import itertools
from random import choice

from modularodm import Q

from framework.auth import Auth
from website.app import init_app
from website import models, security, settings
from tests.factories import NodeFactory

from website.models import NodeLog, Node

fake = Faker()

app = None
CATEGORY_MAP = settings.NODE_CATEGORY_MAP
descriptors = CATEGORY_MAP.keys()

def create_fake_projects(creator, depth, num_logs, level=1, parent=None):
    #auth = Auth(user=creator)
    if depth < 0:
        return None
    descriptor = choice(descriptors) if (level % 2 == 0) else 'project'
    project_title = parent.title + (': ' + CATEGORY_MAP[descriptor]) if (level % 2 == 0) else fake.word()
    project = NodeFactory.build(title=project_title, description=fake.sentences(), creator=creator, parent=parent, is_public=True, privacy='public', category=descriptor)
    project.save()
    for i in range(int(num_logs)):
        project.add_log('wiki_updated', {
            'node': project._id,
        },
            Auth(creator),
        )
    project.save()
    nextlevel = level + 1
    nextdepth = int(depth) - 1
    for i in range(nextlevel):
        create_fake_projects(creator, nextdepth, num_logs, nextlevel, project)
    return project

class Result(object):
    def __init__(self, *args, **kwargs):
        self.keys = kwargs.keys()
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    @property
    def data(self):
        ret = {}
        for k in self.keys:
            ret[k] = getattr(self, k)
        return ret

def get_nodes_recursive(project, include):
    children = list(project.nodes)
    descendants = children + [item for node in project.nodes for item in get_nodes_recursive(node, include)]
    return [project] + [desc for desc in descendants if include(desc)]

def get_aggregate_logs(ids, user, count=100):
    query = Q('params.node', 'in', ids)
    return list(NodeLog.find(query).sort('date').limit(int(count)))

def get_logs(user, project, depth):
    print ("Fetching logs")
    t0 = time.clock()
    nodes = get_nodes_recursive(project, lambda p: p.can_view(Auth(user)))
    ids = [n._id for n in nodes]
    t1 = time.clock()
    logs = get_aggregate_logs(ids, user)
    logs = [l for l in logs]
    t2 = time.clock()
    agg_time = t1 - t0
    fetch_time = t2 - t1
    total_time = t2 - t0
    print ("Took {0}s to fetch {1} logs with a depth of {2}".format(total_time, len(logs), depth))
    return Result(
        total_time=total_time,
        agg_time=agg_time,
        fetch_time=fetch_time,
        num_logs=len(logs),
        depth=depth,
    )

def clean_up(creator, project):
    if len(project.nodes) == 0:
        project.remove_node(Auth(creator))
    else:
        [clean_up(creator, node) for node in project.nodes]

def parse_args():
    parser = argparse.ArgumentParser(description='Create fake data.')
    parser.add_argument('-u', '--user', dest='user', required=True)
    parser.add_argument('-d', '--depth', dest='depth', default=2)
    parser.add_argument('-l', '--num-logs', dest='num_logs', default=10)
    parser.add_argument('-c', '--clean_up', dest='clean_up', default='true')
    return parser.parse_args()

def run(username, depth, num_logs):
    app = init_app('website.settings', set_backends=True, routes=True)
    creator = models.User.find(Q('username', 'eq', username))[0]
    project = create_fake_projects(creator, depth, num_logs)
    ret = get_logs(creator, project, depth)
    if clean_up in ('true', 'True', True):
        clean_up(creator, project)
    return ret

def main():
    args = parse_args()
    run(args.user, int(args.depth or 0), int(args.num_logs or 0))
    sys.exit(0)

if __name__ == '__main__':
    main()
