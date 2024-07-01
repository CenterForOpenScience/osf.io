#!/usr/bin/env python3
import io
import logging
import os
import re
import requests
import zipfile

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from lxml import etree
from urllib.parse import urlparse

from api.base import settings

logger = logging.getLogger(__name__)


def sync_citation_styles(dry_run=False):
    CitationStyle = apps.get_model('osf', 'citationstyle')
    zip_data = io.BytesIO(requests.get(settings.CITATION_STYLES_REPO_URL).content)
    with transaction.atomic():
        with zipfile.ZipFile(zip_data) as zip_file:
            for file_name in [name for name in zip_file.namelist() if name.endswith('.zip') and not name.startswith('dependent')]:
                root = etree.fromstring(zip_file.read(file_name))

                namespace = re.search(r'\{.*\}', root.tag).group()
                title = root.find('{namespace}info/{namespace}title'.format(namespace=f'{namespace}')).text
                has_bibliography = 'Bluebook' in title

                if not has_bibliography:
                    bib = root.find(f'{{{namespace}}}bibliography')
                    layout = bib.find(f'{{{namespace}}}layout') if bib is not None else None
                    has_bibliography = True
                    if layout is not None and len(layout.getchildren()) == 1 and 'choose' in layout.getchildren()[0].tag:
                        choose = layout.find(f'{{{namespace}}}choose')
                        else_tag = choose.find(f'{{{namespace}}}else')
                        if else_tag is None:
                            supported_types = []
                            match_none = False
                            for child in choose.getchildren():
                                types = child.get('type', None)
                                match_none = child.get('match', 'any') == 'none'
                                if types is not None:
                                    types = types.split(' ')
                                    supported_types.extend(types)
                                    if 'webpage' in types:
                                        break
                            else:
                                if len(supported_types) and not match_none:
                                    # has_bibliography set to False now means that either bibliography tag is absent
                                    # or our type (webpage) is not supported by the current version of this style.
                                    has_bibliography = False

                summary = getattr(
                    root.find('{namespace}info/{namespace}summary'.format(namespace=f'{namespace}')), 'text', None
                )
                short_title = getattr(
                    root.find('{namespace}info/{namespace}title-short'.format(namespace=f'{namespace}')), 'text', None
                )
                # Required
                fields = {
                    '_id': os.path.splitext(os.path.basename(file_name))[0],
                    'title': title,
                    'has_bibliography': has_bibliography, 'parent_style': None,
                    'short_title': short_title,
                    'summary': summary
                }

                CitationStyle.objects.update_or_create(**fields)

            for file_name in [name for name in zip_file.namelist() if name.endswith('.zip') and name.startswith('dependent')]:
                root = etree.fromstring(zip_file.read(file_name))

                namespace = re.search(r'\{.*\}', root.tag).group()
                title = root.find('{namespace}info/{namespace}title'.format(namespace=f'{namespace}')).text
                has_bibliography = root.find(f'{{{namespace}}}bibliography') is not None or 'Bluebook' in title

                style_id = os.path.splitext(os.path.basename(file_name))[0]
                links = root.findall('{namespace}info/{namespace}link'.format(namespace=f'{namespace}'))
                for link in links:
                    if link.get('rel') == 'independent-parent':
                        parent_style_id = urlparse(link.get('href')).path.split('/')[-1]
                        parent_style = CitationStyle.objects.get(_id=parent_style_id)

                        if parent_style is not None:
                            summary = getattr(
                                root.find('{namespace}info/{namespace}summary'.format(namespace=f'{namespace}')),
                                'text', None
                            )
                            short_title = getattr(
                                root.find('{namespace}info/{namespace}title-short'.format(namespace=f'{namespace}')),
                                'text', None
                            )

                            parent_has_bibliography = parent_style.has_bibliography
                            fields = {
                                '_id': style_id,
                                'title': title,
                                'has_bibliography': parent_has_bibliography,
                                'parent_style': parent_style_id,
                                'short_title': short_title,
                                'summary': summary
                            }
                            CitationStyle.objects.update_or_create(**fields)
                            break
                        else:
                            logger.debug(f'Unable to load parent_style object: parent {parent_style_id}, dependent style {style_id}')
                else:
                    fields = {
                        '_id': style_id,
                        'title': title,
                        'has_bibliography': has_bibliography,
                        'parent_style': None
                    }
                    CitationStyle.objects.update_or_create(**fields)

        if dry_run:
            raise RuntimeError('This is a dry run rolling back transaction.')


class Command(BaseCommand):
    """Updates citation styles to its current repo URL."""
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        sync_citation_styles(dry_run=dry_run)
