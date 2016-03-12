#!/usr/bin/env python
# encoding: utf-8

import datetime
import logging
import sys
import requests
from modularodm import Q

from website import settings
from website.app import init_app
from website.models import Tag, Conference
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    for conf in Conference.find():
        count = 0
        for tag in Tag.find(Q('lower', 'eq', conf.endpoint.lower())):
            for node in tag.node__tagged.find(Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False)):
                if not dry_run:
                    start_time = node.date_created.strftime('%Y-%m-%d')
                    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
                    url = 'https://osf.io/piwik/index.php?token_auth={}&module=API' \
                          '&method=VisitsSummary.getVisits&format=json&period=range' \
                          '&date={},{}&idSite={}'.format(
                            settings.PIWIK_ADMIN_TOKEN,
                            start_time, today,
                            node.piwik_site_id)
                    resp = requests.get(url)
                    node.visit = resp.json()['value']
                    node.save()
                    count += 1

        logger.info('Get visit counts for {} projects in Conference {}'.format(count, conf.name))
    

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        main(dry_run=dry_run)
