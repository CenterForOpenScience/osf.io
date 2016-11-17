#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Preprint Provicer elements"""

import logging

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import PreprintProvider

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def update_or_create(provider_data):
    provider = PreprintProvider.load(provider_data['_id'])
    if provider:
        for key, val in provider_data.iteritems():
            setattr(provider, key, val)
        changed_fields = provider.save()
        if changed_fields:
            print('Updated {}: {}'.format(provider.name, changed_fields))
        return provider, False
    else:
        new_provider = PreprintProvider(**provider_data)
        new_provider.save()
        provider = PreprintProvider.load(new_provider._id)
        print('Added new preprint provider: {}'.format(provider._id))
        return new_provider, True


def main():
    PREPRINT_PROVIDERS = [
        {
            '_id': 'socarxiv',
            'name': 'SocArXiv',
            'description': 'Open archive of the social sciences',
            'banner_name': 'socarxiv-banner.png',
            'logo_name': 'socarxiv-logo.png',
            'external_url': 'http://socarxiv.org'
        },
        {
            '_id': 'osf',
            'name': 'Open Science Framework',
            'description': 'A scholarly commons to connect the entire research cycle',
            'banner_name': 'cos-banner.png',
            'logo_name': 'cos-logo.png',
            'external_url': 'https://osf.io/preprints/'
        },
        {
            '_id': 'engrxiv',
            'name': 'Engineering Archive',
            'description': 'Engineering Archive, the eprint server for engineering.',
            'banner_name': 'engarxiv-banner.png',
            'logo_name': 'engarxiv-logo.png',
            'external_url': 'http://engrxiv.org'
        },
        {
            '_id': 'psyarxiv',
            'name': 'PsyArXiv',
            'description': 'A free preprint service for the psychological sciences.',
            'banner_name': 'psyarxiv-banner.png',
            'logo_name': 'psyarxiv-logo.png',
            'external_url': 'http://psyarxiv.org'
        },
    ]

    init_app(routes=False)
    with TokuTransaction():
        for provider_data in PREPRINT_PROVIDERS:
            update_or_create(provider_data)


if __name__ == '__main__':
    main()
