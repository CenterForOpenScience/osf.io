"""

Get indexes:

    http :9201/osf_preprintdownload*/ | jq 'keys'

Get total count of preprintdownloads:

    http :9201/osf_preprintdownload*/_count

Delete data:

    http DELETE :9201/_template/osf_*
    http DELETE :9201/osf_*
"""
import sys
from website.app import setup_django
import datetime as dt
import logging
setup_django()
import random
from django.utils import timezone

from osf.metrics import PreprintDownload
from osf.models import PreprintProvider, PreprintService
from tests.base import fake

for logger_name in [
    'elasticsearch',
    'urllib3.connectionpool',
]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def populate_preprint_downloads(n):
    preprints = PreprintService.objects.filter(created__gt=timezone.now() - dt.timedelta(days=30), is_published=True)
    max_idx = preprints.count()
    for _ in range(n):
        random_idx = random.randint(0, max_idx)
        preprint = PreprintService.objects.select_related('provider').all()[random_idx]
        print('Creating random download for {} ({})'.format(preprint._id, preprint.provider._id))
        PreprintDownload.record(
            timestamp=fake.date_this_year(before_today=True, after_today=False),
            provider_id=preprint.provider._id,
            user_id=fake.lexify('?????'),
            preprint_id=preprint._id,
            version=random.choice(['1', '2', '3']),
            path='/' + fake.lexify('????????????????')
        )
    print('Saved {} metrics'.format(n))


def populate(n):
    provider_ids = list(PreprintProvider.objects.values_list('_id', flat=True))
    for _ in range(n):
        provider_id = random.choice(provider_ids)
        print('Creating random download for {}'.format(provider_id))
        PreprintDownload.record(
            timestamp=fake.date_this_year(before_today=True, after_today=False),
            provider_id=provider_id,
            user_id=fake.lexify('?????'),
            preprint_id=fake.lexify('?????'),
            version=random.choice(['1', '2', '3']),
            path='/' + fake.lexify('????????????????')
        )
    print('Saved {} metrics'.format(n))


def top_providers_by_downloads():
    qs = PreprintDownload.get_top_by_count(
        qs=PreprintProvider.objects.all(),
        model_field='_id',
        metric_field='provider_id',
        size=10,
        annotation='download_count',
    )[:10]
    for each in qs:
        print('{}: {}'.format(each._id, each.download_count))
    total = sum([each.download_count for each in qs])
    print('Total: {}'.format(total))


def top_preprints_by_downloads():
    qs = PreprintDownload.get_top_by_count(
        qs=PreprintService.objects.all(),
        model_field='guids___id',
        metric_field='preprint_id',
        size=10,
        annotation='download_count',
    ).select_related('provider')[:10]
    for each in qs:
        print('{}: {} ({})'.format(each._id, each.download_count, each.provider._id))
    total = sum([each.download_count for each in qs])
    print('Total: {}'.format(total))


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 0:
        if args[0] == 'populate':
            populate_preprint_downloads(int(args[1]))
        elif args[0] == 'preprints':
            top_preprints_by_downloads()
        else:
            top_providers_by_downloads()
