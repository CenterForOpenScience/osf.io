# -*- coding: utf-8 -*-

"""Create mailing lists for all top-level projects
"""

import sys
import logging
import requests

from website.app import init_app
from website.util import api_url_for
from website.settings import MAILGUN_API_KEY, SHORT_DOMAIN, DOMAIN

logger = logging.getLogger(__name__)


def main():
    init_app()
    dry = 'dry' in sys.argv
    if not dry:
        requests.post(
            "https://api.mailgun.net/v3/routes",
            auth=("api", MAILGUN_API_KEY),
            data={"priority": 0,
                  "description": "Project Mailing Route",
                  "expression": 'match_recipient(".{}@{}")'.format('{5}', settings.SHORT_DOMAIN), ## Any 5-char GUID@osf.io
                  "action": ["forward('{}api/v1/discussions/messages/')".format(DOMAIN), "stop()"]})
    logger.info('Finished creating route')

if __name__ == '__main__':
    main()

