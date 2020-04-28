# -*- coding: utf-8 -*-
import logging
import os
import csv
import requests
import datetime
import zipfile
from django.utils import timezone
from addons.osfstorage.models import UserSettings
from osf.models import OSFUser
from django.db.models import F
from io import BytesIO, StringIO

from website.settings import (
    USA,
    GERMANY,
    CANADA,
    AUSTRALIA,
    DS_METRICS_OSF_TOKEN,
    DS_METRICS_BASE_FOLDER
)

USER_PER_CSV = 10000

from django.core.management.base import BaseCommand

from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)
FILENAME = 'osf_international_user_metrics.csv'


def get_user_count_by_region(region_name):
    return UserSettings.objects.filter(
        default_region__name=region_name,
        owner__is_active=True,
        owner__merged_by=None,
    ).count()


def append_to_csv(url, rows, token):
    headers = {'Authorization': 'Bearer {}'.format(token)}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    fieldnames = list(rows[0].keys())
    file = StringIO(resp.content.decode())

    file.seek(0, os.SEEK_END)

    w = csv.DictWriter(file, fieldnames=fieldnames)
    w.writerows(rows)
    file.seek(0)
    data = file.read()

    resp = requests.put(
        url,
        data=data,
        headers=headers
    )
    resp.raise_for_status()


def create_csv_header(fieldnames):
    file = StringIO()
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    file.seek(0)
    return file.read()


def upload_to_file(url, data, token):
    headers = {'Authorization': 'Bearer {}'.format(token)}
    resp = requests.put(
        url,
        data=data,
        headers=headers
    )
    resp.raise_for_status()


def get_or_create_file(base_folder_url, filename, token, data):
    headers = {'Authorization': 'Bearer {}'.format(token)}

    resp = requests.get(base_folder_url, headers=headers)
    resp.raise_for_status()

    base_folder_data = resp.json()['data']
    children_link = base_folder_data['relationships']['files']['links']['related']['href']
    resp = requests.get(children_link, headers=headers)
    resp.raise_for_status()

    children_json = resp.json()['data']
    try:
        return next(x['links']['upload'] for x in children_json if x['attributes']['name'] == filename)
    except StopIteration:
        resp = requests.put(
            base_folder_data['links']['upload'] + '?name={}&kind=file'.format(filename),
            data=data,
            headers=headers
        )
        resp.raise_for_status()
        return resp.json()['data']['links']['upload']


def create_zip(zip_name, file_names, files):
    buff = BytesIO()
    with zipfile.ZipFile(buff, mode='w') as zip_file:
        zip_file.filename = zip_name
        for i, data in enumerate(files):
            zip_file.writestr(file_names[i], data)

    buff.seek(0)
    return buff.read()


def create_csv(rows):
    file = StringIO()
    writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    file.seek(0)
    return file.read()


def update_international_users_counts(dry_run=True):
    # International users aggregate counts
    new_row = [{
        'date': timezone.now().strftime('%Y-%m-%d'),
        'users_usa_storage': get_user_count_by_region(USA),
        'users_germany_storage': get_user_count_by_region(GERMANY),
        'users_canada_storage': get_user_count_by_region(CANADA),
        'users_australia_storage': get_user_count_by_region(AUSTRALIA),
    }]

    fieldnames = list(new_row[0].keys())

    # Check if file exists add header if so.
    if not dry_run:
        upload_link = get_or_create_file(
            DS_METRICS_BASE_FOLDER,
            FILENAME,
            DS_METRICS_OSF_TOKEN,
            create_csv_header(fieldnames)
        )
    else:
        logger.info(f'[DRY RUN] for {FILENAME} uploaded to {DS_METRICS_BASE_FOLDER}')

    # Now it definitely exists, download the old add the new and upload.
    if not dry_run:
        append_to_csv(upload_link, new_row, DS_METRICS_OSF_TOKEN)
    else:
        logger.info(f'[DRY RUN] for {new_row} uploaded to {DS_METRICS_BASE_FOLDER}')


def upload_users_raw_data(dry_run=True):
    """ This creates and uploads a zip file containing CSVs with relevant user data."""
    # Raw user data
    rows = OSFUser.objects.annotate(
        # Rename region_id for less awkward column title
        region_id=F('addons_osfstorage_user_settings__default_region_id')
    ).values('username', 'id', 'region_id')

    chunks = [rows[i:i + USER_PER_CSV] for i in range(0, len(rows), USER_PER_CSV)]

    filenames = []
    files = []
    for i, chunk in enumerate(chunks):
        files.append(create_csv(chunk))
        filenames.append('data-usage-raw-user-{}.csv'.format(i))

    zip_filename = 'data_storage_raw_users_{}.zip'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
    zip_data = create_zip(zip_filename, filenames, files)

    if not dry_run:
        upload_link = get_or_create_file(DS_METRICS_BASE_FOLDER, zip_filename, DS_METRICS_OSF_TOKEN, zip_data)
        upload_to_file(upload_link, zip_data, DS_METRICS_OSF_TOKEN)
    else:
        logger.info(f'[DRY RUN] {zip_filename} uploaded to {DS_METRICS_BASE_FOLDER}')


@celery_app.task(name='management.commands.international_user_metrics')
def main(dry_run):
    update_international_users_counts(dry_run)
    upload_users_raw_data(dry_run)


class Command(BaseCommand):
    help = """This is meant to run nightly and save various usage metrics to a csv file."""

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        main(dry_run)
