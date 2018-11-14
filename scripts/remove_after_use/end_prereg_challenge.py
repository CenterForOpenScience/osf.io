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
    switch.active = True
    prereg_schema = RegistrationSchema.objects.get(name='OSF Preregistration')
    prereg_schema.active = True
    if dry_run:
        logger.warn('This is a dry run')
    else:
        switch.save()
        prereg_schema.save()


@celery_app.task(name='scripts.remove_after_use.end_prereg_challenge')
def run_main(dry_run=True):
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)


if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
