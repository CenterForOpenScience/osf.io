""" Changes existing MetaSchemas to a consistent format that
adheres to what is expected for JSONEditor
"""

import sys
import logging

from nose.tools import *

from website import models
from website.app import init_app
from scripts import utils as scripts_utils
from website.project.metadata.schemas import OSF_META_SCHEMAS

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
            'description': question['caption'] if question['caption'] else ''
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
        'title': old_page['title'] if old_page['title'] else '',
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

    return new_page


def main(source=OSF_META_SCHEMAS, dry_run=True):
    init_app(routes=False)
    count = 0

    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all MetaSchemas")
        models.MetaSchema.remove()

    for schema in source:
        valid_schema = {
            'name': schema['name'],
            'version': schema['version'] if schema['version'] else 1,
            'type': 'object',
            'description': schema['description'] if 'description' in schema else '',
            'fulfills': schema['fulfills'] if 'fulfills' in schema else list(),
            'pages': list()
        }

        num_pages = 1
        if 'schema' in schema:
            for page in schema['schema']['pages']:
                new_page = construct_page(page, num_pages)
                valid_schema['pages'].append(new_page)
                num_pages += 1
        else:
            for page in schema['pages']:
                new_page = construct_page(page, num_pages)
                valid_schema['pages'].append(new_page)
                num_pages += 1

        count += 1

        if not dry_run:
            updated_schema = models.MetaSchema(**valid_schema)
            updated_schema.save()

    logger.info('Done with {} schemas migrated'.format(count))


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run=dry_run)
