#!/usr/bin/env python
# encoding: utf-8

import logging
import json
import requests
import urllib

from modularodm import Q

from framework.celery_tasks import app as celery_app

from website import settings
from website.app import init_app
from framework.transactions.context import TokuTransaction
from website.models import Tag, Conference, Node
from website.files.models import StoredFileNode
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    init_app(routes=False)
    for conf in Conference.find():
        count = 0
        for tag in Tag.find(Q('lower', 'eq', conf.endpoint.lower())):
            for node in Node.find(Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False) & Q('tags', 'eq', tag)):
                record = next(
                    x for x in
                    StoredFileNode.find(
                        Q('node', 'eq', node) &
                        Q('is_file', 'eq', True)
                    ).limit(1)
                ).wrapped()

                if not dry_run:
                    query = [{"property_name":"page.info.path",
                              "operator":"eq",
                              "property_value": record._id }]
                    query = urllib.quote(json.dumps(query))

                    url = 'https://api.keen.io/3.0/projects/{}/queries/count' \
                          '?api_key={}&event_collection=pageviews&timezone=UTC&timeframe' \
                          '=this_14_days&filters={}'.format(
                            settings.KEEN['public']['project_id'],
                            settings.KEEN['public']['read_key'],
                            query
                    )

                    resp = requests.get(url)
                    record.visit = resp.json()['result']
                    record.save()
                    count += 1

        logger.info('Get visit counts for {} projects in Conference {}'.format(count, conf.name))
    

@celery_app.task(name='scripts.meeting_visit_count')
def run_main(dry_run=True):
    scripts_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry_run=dry_run)
