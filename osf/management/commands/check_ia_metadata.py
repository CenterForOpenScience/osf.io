import re
import requests
from django.core.management.base import BaseCommand
from osf.models import Registration
from website import settings
import logging
from django.db.models import F


logger = logging.getLogger(__name__)


class IAMetadataError(Exception):
    def __init__(self, message=None, fields=None):
        self.message = message
        self.fields = fields


get_ia_field = lambda field: Registration.IA_MAPPED_NAMES.get(field, field)

mirrored_attrs = list(Registration.SYNCED_WITH_IA)

mirrored_fields = mirrored_attrs + ['subjects', 'tags', 'affiliated_institutions']
mirrored_relationships = [
    'subjects__text',
    'affiliated_institutions__name',
    'tags__name',
]


def check_ia_metadata(collection=settings.IA_ROOT_COLLECTION, guids=None):
    item_data = requests.get(
        'https://archive.org/advancedsearch.php'
        f'?q=collection%3A({collection}) AND identifier:(osf-registrations-*-{settings.ID_VERSION})'
        '&fl[]='
        + '&fl[]='.join([get_ia_field(field) for field in mirrored_fields])
        + '&fl[]=identifier'
        '&rows=100000'
        '&output=json'
    ).json()['response']['docs']
    item_data = sorted(item_data, key=lambda x: x['identifier'])

    archived_registrations = Registration.objects.filter(ia_url__isnull=False).exclude(ia_url='').order_by(
        '-ia_url',
    )

    if guids:
        archived_registrations = archived_registrations.filter(guids___id__in=guids)
        item_data = [
            item
            for item in item_data
            if [re.match(guid, item['identifier']) for guid in guids]
        ]

    registration_data = archived_registrations.values(
        *mirrored_attrs,
        'ia_url',
    ).annotate(
        subjects=F('subjects__text'),
        affiliated_institutions=F('affiliated_institutions__name'),
        tags=F('tags__name'),
    )

    if archived_registrations.count() != len(item_data):
        raise IAMetadataError(
            message=f' We have {archived_registrations.count()} registrations with IA urls, but there are'
            f' {len(item_data)} IA items with our id in our collection'
        )

    desynced = {}
    for ia_item, osf_registration in zip(item_data, registration_data):
        for field, osf_value in osf_registration.items():
            ia_url = osf_registration['ia_url']
            ia_value = ia_item.get(Registration.IA_MAPPED_NAMES.get(field, field), None)
            if osf_value != ia_value and field not in (
                'ia_url',
                'modified',
                'moderation_state',
            ):
                if not desynced.get(ia_url):
                    desynced[ia_url] = {'fields': []}
                desynced[ia_url]['fields'].append(field)

    if desynced:
        raise IAMetadataError(fields=desynced, message='some fields weren\'t synced')


class Command(BaseCommand):
    '''
    Checks all IA items in collection to see if they are synced with the OSF
    '''

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--collection',
            type=str,
            action='store',
            dest='ia_collection',
            help='The Internet Archive collection that we are checking for parity',
        )

    def handle(self, *args, **options):
        collection = options.get('collection', settings.IA_ROOT_COLLECTION)
        check_ia_metadata(collection)
