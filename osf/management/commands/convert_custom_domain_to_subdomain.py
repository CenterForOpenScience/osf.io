import re
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from scripts import utils as script_utils
from osf.models import PreprintProvider
from website import settings
logger = logging.getLogger(__name__)


def get_domain(provider):
    osf_domain = settings.DOMAIN.lstrip(settings.PROTOCOL)

    # localhost
    if osf_domain.startswith('localhost:5000/'):
        return f'{settings.PROTOCOL}{provider._id}.localhost:5000/'
    # staging
    elif osf_domain.startswith('staging'):
        return f'{settings.PROTOCOL}{provider._id}.staging.osf.io/'
    # staging2
    elif osf_domain.startswith('staging2'):
        return f'{settings.PROTOCOL}{provider._id}.staging2.osf.io/'
    # staging3
    elif osf_domain.startswith('staging3'):
        return f'{settings.PROTOCOL}{provider._id}.staging3.osf.io/'
    # test
    elif osf_domain.startswith('test'):
        return f'{settings.PROTOCOL}{provider._id}.staging3.osf.io/'
    # host number
    elif re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,}\/', osf_domain):
        return f'{settings.PROTOCOL}{provider._id}.localhost:5000/'
    else:
        raise NotImplementedError('Domain not supported')


def set_provider_domains(really_delete=False):
    providers = PreprintProvider.objects.filter(domain_redirect_enabled=True)
    for provider in providers:
        new_subdomain = get_domain(provider)
        logger.info(f'provider with domain {provider.domain} is being changed to {new_subdomain}')
        provider.domain = new_subdomain
        if really_delete:
            provider.save()

class Command(BaseCommand):
    """
    Changes preprint provider custom domains to subdomains of osf.io
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--i-am-really-sure-about-this',
            action='store_true',
            dest='really_update',
            help='convert the subdomain'
        )

    def handle(self, *args, **options):
        really_update = options.get('really_update', False)
        if really_update:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            set_provider_domains(really_update)
            if not really_update:
                raise RuntimeError('Dry run -- transaction rolled back')
            logger.info('Committing...')
