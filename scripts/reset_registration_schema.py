"""
This migration subscribes each user to USER_SUBSCRIPTIONS_AVAILABLE if a subscription
does not already exist.
"""

import logging
import sys

from website.app import setup_django
setup_django()

from website.app import init_app
from django.apps import apps
from django.db.transaction import commit
from osf.utils.migrations import ensure_schemas
from osf.utils.sanitize import strip_html
from osf.models import RegistrationSchema, RegistrationSchemaBlock
from osf.utils.migrations import create_schema_blocks_for_question, create_schema_block

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info(sys.argv)
    init_app(routes=False)

    schema_name = sys.argv[1]

    # delete schema if it exists
    schema = RegistrationSchema.objects.filter(name=schema_name).first()
    if schema is not None:
        RegistrationSchemaBlock.objects.filter(schema_id=schema).delete()
        schema.delete()

    # create schema
    ensure_schemas(apps)
    schema = RegistrationSchema.objects.get(name=schema_name)
    for page in schema.schema['pages']:
        create_schema_block(
            apps,
            schema.id,
            'page-heading',
            display_text=strip_html(page.get('title', '')),
            help_text=strip_html(page.get('description', '')),
            concealment_page_navigator=strip_html(page.get('concealment_page_navigator', False))
        )
        for question in page['questions']:
            create_schema_blocks_for_question(apps, schema, question)
