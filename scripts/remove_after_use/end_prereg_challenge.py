import sys
import logging

from website.app import setup_django
setup_django()

from waffle.models import Switch

from framework.celery_tasks import app as celery_app


from scripts.utils import add_file_logger
from osf.models import RegistrationSchema

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):

    switch = Switch.objects.get(name='osf_preregistration')
    logger.info('Setting {} switch to active'.format(switch.name))
    switch.active = True
    prereg_challenge_schema = RegistrationSchema.objects.get(name='Prereg Challenge')
    logger.info('Setting {} schema to inactive'.format(prereg_challenge_schema.name))
    prereg_challenge_schema.active = False
    prereg_schema = RegistrationSchema.objects.get(name='OSF Preregistration')
    logger.info('Setting {} schema to active'.format(prereg_schema.name))
    prereg_schema.active = True
    logger.info('Setting {} schema to visible'.format(prereg_schema.name))
    prereg_schema.visible = True
    if dry_run:
        logger.warn('This is a dry run')
    else:
        switch.save()
        prereg_schema.save()
        prereg_challenge_schema.save()


@celery_app.task(name='scripts.remove_after_use.end_prereg_challenge')
def run_main(dry_run=True):
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)


if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
