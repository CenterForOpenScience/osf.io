from website import models

import sys
import argparse
from modularodm.query.querydialect import DefaultQueryDialect as Q

from website.app import init_app

# python -m scripts.create_custom_citation --user fred@cos.io -c This is your citation


def parse_args():
    parser = argparse.ArgumentParser(description='Create fake data.')
    parser.add_argument('-u', '--user', dest='user', required=True)
    parser.add_argument('-p', '--project', dest='projectID', required=True)
    parser.add_argument('-c', '--citation', dest='citation', required=True)
    return parser.parse_args()

def create_fake_citaion(creator, project, text):
    project.nonContributorCitations.append(text)
    project.save()
    return project


def main():
    args = parse_args()
    creator = models.User.find(Q('username', 'eq', args.user))[0]
    project = models.Node.find(Q('id', 'eq', args.projectId))[0]
    create_fake_citaion(creator, project, args.citation)
    sys.exit(0)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()