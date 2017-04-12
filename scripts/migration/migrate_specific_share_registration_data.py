""" Sends specified registrations to SHARE """
import argparse
import json
import logging
import sys
import django
from django.db import transaction
django.setup()

from osf.models import AbstractNode
from scripts import utils as script_utils
from website import settings
from website.app import init_app
from website.project.tasks import on_registration_updated


logger = logging.getLogger(__name__)

def migrate(registrations):
    print registrations
    assert settings.SHARE_URL, 'SHARE_URL must be set to migrate.'
    assert settings.SHARE_API_TOKEN, 'SHARE_API_TOKEN must be set to migrate.'
    registrations_count = len(registrations)

    count = 0

    logger.info('Preparing to migrate {} registrations.'.format(registrations_count))
    for registration_id in registrations:
        count += 1
        logger.info('{}/{} - {}'.format(count, registrations_count, registration_id))
        registration = AbstractNode.load(registration_id)
        assert registration.type == 'osf.registration'
        on_registration_updated(registration)
        logger.info('Registration {} was sent to SHARE.'.format(registration_id))


def main():
    parser = argparse.ArgumentParser(
        description='Changes the provider of specified PreprintService objects'
    )

    parser.add_argument(
        '--targets',
        action='store',
        dest='targets',
        help='List of targets, of form {"data": ["registration_id", ...]}',
    )
    pargs = parser.parse_args()
    script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with transaction.atomic():
        migrate(json.loads(pargs.targets)['data'])

if __name__ == "__main__":
    main()