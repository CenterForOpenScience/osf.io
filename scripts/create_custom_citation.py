from website import models

import sys
import argparse
from website.util import sanitize
from modularodm.query.querydialect import DefaultQueryDialect as Q

from website.app import init_app

# python -m scripts.create_custom_citation --user fred@cos.io


def parse_args():
    parser = argparse.ArgumentParser(description='Create fake data.')
    parser.add_argument('-u', '--user', dest='user', required=True)
    parser.add_argument('-p', '--project', dest='projectID', required=True)
    return parser.parse_args()

def create_fake_citaion(creator, project):
    citation ={
            'id': raw_input("Id: "),
            'title': sanitize.unescape_entities(raw_input("Title: ")),
            'publisher': raw_input("Publisher: "),
            'type': raw_input("Media Type: "),
            'URL': raw_input("URL: "),
            'DOI': raw_input("DOI: "),
            'Issued': raw_input("Issued: "),
            'locator': raw_input("Locator: "),
            'label': raw_input("Label: ")
    }
    authors = []
    end_author = ''
    while end_author != 'no':
        given_name = raw_input("Author's first name:")
        family_name = raw_input("Author's last name:")

        author = {
            'given':given_name,
            'family':family_name,
        }
        end_author = raw_input("Type 'no' if there are no more authors otherwise press enter:")

        authors.append(author)

    citation['author'] = authors
    project.nonContributorCitations.append(citation)
    project.save()
    return project


def main():
    args = parse_args()
    creator = models.User.find(Q('username', 'eq', args.user))[0]
    project = models.Node.find(Q('_id', 'eq', args.projectID))[0]
    create_fake_citaion(creator, project)
    sys.exit(0)


if __name__ == '__main__':
    init_app(set_backends=True, routes=True)
    main()