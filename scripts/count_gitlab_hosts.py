"""
Meant to count the frequency of gitlab host names, so we can create a whitelist or do a better migration.
"""

import logging

import django
from django.utils import timezone
from django.db import transaction
django.setup()

from osf.models import ExternalAccount

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():

    hosts = list(ExternalAccount.objects.filter(provider='gitlab').values_list('oauth_secret', flat=True))
    hosts_keys = set(hosts)

    hosts_dict = {}
    for key in hosts_keys:
        logger.info("{} | Host name: {} ".format(hosts.count(key), key))

    return hosts_dict


if __name__ == "__main__":
    main()
