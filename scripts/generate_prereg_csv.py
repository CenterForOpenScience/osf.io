# -*- coding: utf-8 -*-
import io
import os
import csv
import gzip
import logging

from website.app import setup_django
setup_django()

from admin.base import utils
from django.conf import settings
from django.utils import timezone
from admin.pre_reg import serializers


from api.base.utils import waterbutler_api_url_for
from framework.celery_tasks import app as celery_app
from scripts import utils as scripts_utils

import requests
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))

def generate_prereg_csv():
    drafts = list(map(serializers.serialize_draft_registration,
                   utils.get_submitted_preregistrations()))

    keys = drafts[0].keys()
    keys.remove('registration_schema')
    output = io.BytesIO()
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    for draft in drafts:
        draft.pop('registration_schema')
        draft.update({'initiator': draft['initiator']['username']})
        writer.writerow(
            {k: v.encode('utf8') if isinstance(v, unicode) else v
             for k, v in draft.items()}
        )
    return output

def main():
    prereg_csv = generate_prereg_csv()

    filename = 'prereg_{}.csv.gz'.format(timezone.now().isoformat())

    output = io.BytesIO()
    with gzip.GzipFile(filename=filename, mode='wb', fileobj=output) as gzip_obj:
        gzip_obj.write(prereg_csv.getvalue())

    if settings.PREREG_DATA_STORE_GUID and settings.PREREG_DATA_STORE_TOKEN:
        resp = requests.put(waterbutler_api_url_for(settings.PREREG_DATA_STORE_GUID, 'osfstorage', _internal=True) + '?name={}&kind=file'.format(filename),
                     data=output.getvalue(),
                     headers={'Authorization': 'Bearer {}'.format(settings.PREREG_DATA_STORE_TOKEN)})

        if resp.status_code == 201:
            logger.info('Prereg data uploaded properly')
        else:
            logger.info('Prereg data failed with code {}'.format(resp.status_code))


@celery_app.task(name='scripts.generate_prereg_csv')
def run_main():
    scripts_utils.add_file_logger(logger, __file__)
    main()

if __name__ == '__main__':
    main()
