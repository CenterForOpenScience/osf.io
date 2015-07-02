""" Changes existing MetaSchemas to a consistent format that
adheres to what is expected for JSONEditor
"""

import re
import ast
import sys
import logging

from nose.tools import *
from modularodm import Q

from website import models
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def find_question_type(question):
    if question['type'] == 'textfield':
        return {
            'type': 'string',
            'format': 'textarea',
            'title': question['label'],
            'description': question['caption'] if 'caption' in question else '',
        }
    elif question['type'] == 'string':
        return {
            'type': 'string',
            'format': 'text',
            'title': question['label'],
            'description': question['caption'] if 'caption' in question else '',
        }
    elif question['type'] == 'select':
        return {
            'type': 'array',
            'format': 'select',
            'items': {
                'type': 'string',
                'enum': [option for option in question['options']]
            },
            'title': question['label'],
            'description': question['caption'] if 'caption' in question else ''
        }
    elif question['type'] == 'checkbox':
        return {
            'type': 'multiselect',
            'items': [option for option in question['options']],
            'title': question['label'],
            'description': question['caption'] if 'caption' in question else ''
        }
    elif question['type'] == 'section':
        return [find_question_type(sq) for sq in question['contents']]
    else:
        return False


def construct_page(old_page, num_pages):
    new_page = {
        'id': 'page{}'.format(num_pages),
        'title': old_page['title'] if 'title' in old_page else '',
        'type': 'object',
        'questions': list()
    }

    num_questions = 1
    if 'contents' in old_page:
        for item in old_page['contents']:
            question_type = find_question_type(item)
            if question_type:
                question = {
                    'id': num_questions,
                    'title': new_page['title'],
                    'type': 'object',
                    'properties': {
                        'q{}'.format(num_questions): {
                            'type': question_type['type'],
                            'format': question_type['format'],
                            'title': question_type['title'],
                            'description': question_type['description']
                        }
                    }
                }
                new_page['questions'].append(question)
                num_questions += 1
    elif 'questions' in old_page:

        # already matches our schema
        new_page['questions'].append(old_page['questions'])
    else:
        if old_page:
            for page in old_page:
                new_page['questions'].append({
                    'id': num_questions,
                    'title': new_page['title'],
                    'type': 'object',
                    'properties': {
                        page: old_page[page]
                    }
                })
                num_questions += 1

    return new_page


def get_registered_nodes():
    return models.Node.find(
        Q('is_registration', 'eq', True)
    )


def main(dry_run=True):
    init_app(routes=False)
    count = 0

    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all registrations")
        models.MetaSchema.remove()

    for node in get_registered_nodes():
        for schema in node.registered_meta:
            values = ast.literal_eval(node.registered_meta.get(schema))

            from pprint import pprint;

            pprint(values)

            # in some schemas, answers are just stored as { 'itemX': 'answer' }
            matches = dict()
            for val in values:
                m = re.search("item[0-9]*", val)
                if m is not None or val == 'datacompletion' or val == 'summary':
                    matches[val] = values[val]

            valid_schema = {
                'name': schema,
                'version': schema['version'] if 'version' in schema else 1,
                'type': 'object',
                'description': schema['description'] if 'description' in schema else '',
                'fulfills': schema['fulfills'] if 'fulfills' in schema else list(),
                'pages': list(),
                'embargoEndDate': values['embargoEndDate'],
                'registrationChoice': values['registrationChoice'],
            }

        num_pages = 1
        if 'schema' in schema:
            for page in schema['schema']['pages']:
                new_page = construct_page(page, num_pages)
                valid_schema['pages'].append(new_page)
                num_pages += 1
        elif 'pages' in schema:
            for page in schema['pages']:
                new_page = construct_page(page, num_pages)
                valid_schema['pages'].append(new_page)
                num_pages += 1
        else:
            new_page = construct_page(matches, num_pages)
            valid_schema['pages'].append(new_page)
            num_pages += 1

        count += 1

        if not dry_run:
            node.registered_meta = valid_schema
            node.save()

    logger.info('Done with {} nodes migrated'.format(count))


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main()
