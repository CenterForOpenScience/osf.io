"""Due to a bug in Node::fork_node, the user creating a fork was not saved
as the creator of the forked node. This script identifies forks without a
creator and imputes the 0th contributor as the creator.

Dry run: python -m scripts/consistency/impute_creator
Real: python -m scripts/consistency/impute_creator false

"""

from website.app import init_app
from website import models
from framework import Q

app = init_app()

def impute_creator(dry_run=True):
    no_creator = models.Node.find(
        Q('creator', 'eq', None) &
        Q('contributors', 'ne', [])
    )
    for node in no_creator:
        print u'Imputing creator {} for node title {}'.format(
            node.contributors[0].fullname,
            node.title,
        )
        if not dry_run:
            node.creator = node.contributors[0]
            node.save()

if __name__ == '__main__':
    import sys
    dry_run = len(sys.argv) == 1 or sys.argv[1].lower() not in ['f', 'false']
    impute_creator(dry_run=dry_run)
