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
            '_id': 'osf',
            'name': 'Open Science Framework',
            'logo_name': 'cos-logo.png',
            'description': 'A scholarly commons to connect the entire research cycle',
            'banner_name': 'cos-banner.png',
            'external_url': 'https://osf.io/preprints/',
            'example': 'khbvy',
            'advisory_board': '',
            'email_contact': '',
            'email_support': '',
            'social_twitter': '',
            'social_facebook': '',
            'social_instagram': '',
            'licenses_acceptable': [],
            'header_text': '',
            'subjects_acceptable': [],
        },
        {
            '_id': 'engrxiv',
            'name': 'engrXiv',
            'logo_name': 'engrxiv-logo.png',
            'description': 'The open archive of engineering.',
            'banner_name': 'engrxiv-banner.png',
            'external_url': 'http://engrxiv.org',
            'example': '',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                    <p class="m-b-lg">engrXiv is directed by a steering committee of engineers and members of the engineering librarian community. They are:</p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><a href="http://libguides.mit.edu/profiles/psayers">Phoebe Ayers</a>, librarian, Massachusetts Institute of Technology</li>
                        <li><a href="http://stem.gwu.edu/lorena-barba">Lorena A. Barba</a>, aerospace engineer, The George Washington University</li>
                        <li><a href="http://www.devinberg.com/">Devin R. Berg</a>, mechanical engineer, University of Wisconsin-Stout</li>
                        <li><a href="http://mime.oregonstate.edu/people/dupont">Bryony Dupont</a>, mechanical engineer, Oregon State University</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><a href="http://directory.uark.edu/people/dcjensen">David Jensen</a>, mechanical engineer, University of Arkansas</li>
                        <li><a href="http://biomech.media.mit.edu/people/">Kevin Moerman</a>, biomechanical engineer, Massachusetts Institute of Technology</li>
                        <li><a href="http://mime.oregonstate.edu/people/kyle-niemeyer">Kyle Niemeyer</a>, mechanical engineer, Oregon State University</li>
                        <li><a href="http://www.douglasvanbossuyt.com/">Douglas Van Bossuyt</a>, mechanical engineer, Colorado School of Mines</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+engrxiv@osf.io',
            'email_support': 'support+engrxiv@osf.io',
            'social_twitter': 'engrxiv',
            'social_facebook': 'engrXiv',
            'social_instagram': 'engrxiv',
            'licenses_acceptable': [],
            'header_text': '',
            'subjects_acceptable': [],
        },
        {
            '_id': 'psyarxiv',
            'name': 'PsyArXiv',
            'logo_name': 'psyarxiv-logo.png',
            'description': 'A free preprint service for the psychological sciences.',
            'banner_name': 'psyarxiv-banner.png',
            'external_url': 'http://psyarxiv.com',
            'example': '',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Jack Arnal</b>, McDaniel College</li>
                        <li><b>David Barner</b>, University of California, San Diego</li>
                        <li><b>Benjamin Brown</b>, Georgia Gwinnett College</li>
                        <li><b>David Condon</b>, Northwestern University</li>
                        <li><b>Will Cross</b>, North Carolina State University Libraries</li>
                        <li><b>Anita Eerland</b>, Utrecht University</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Chris Hartgerink</b>, Tilburg University</li>
                        <li><b>Alex Holcombe</b>, University of Sydney</li>
                        <li><b>Jeff Hughes</b>, University of Waterloo</li>
                        <li><b>Don Moore</b>, University of California, Berkeley</li>
                        <li><b>Sean Rife</b>, Murray State University</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+psyarxiv@osf.io',
            'email_support': 'support+psyarxiv@osf.io',
            'social_twitter': 'psyarxiv',
            'social_facebook': 'PsyArXiv',
            'social_instagram': 'psyarxiv',
            'licenses_acceptable': [],
            'header_text': '',
            'subjects_acceptable': [],
        },
        {
            '_id': 'socarxiv',
            'name': 'SocArXiv',
            'logo_name': 'socarxiv-logo.png',
            'description': 'Open archive of the social sciences',
            'banner_name': 'socarxiv-banner.png',
            'external_url': 'http://socarxiv.org',
            'example': '',
            'advisory_board': '''
                <div class="col-xs-12">
                    <h2>Steering Committee</h2>
                    <p class="m-b-lg"></p>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Elizabeth Popp Berman</b>, University at Albany SUNY</li>
                        <li><b>Chris Bourg</b>, Massachusetts Institute of Technology</li>
                        <li><b>Neal Caren</b>, University of North Carolina at Chapel Hill</li>
                        <li><b>Philip N. Cohen</b>, University of Maryland, College Park</li>
                        <li><b>Tressie McMillan Cottom</b>, Virginia Commonwealth University</li>
                    </ul>
                </div>
                <div class="col-xs-6">
                    <ul>
                        <li><b>Tina Fetner</b>, McMaster University</li>
                        <li><b>Dan Hirschman</b>, Brown University</li>
                        <li><b>Rebecca Kennison</b>, K|N Consultants</li>
                        <li><b>Judy Ruttenberg</b>, Association of Research Libraries</li>
                    </ul>
                </div>
            ''',
            'email_contact': 'contact+socarxiv@osf.io',
            'email_support': 'support+socarxiv@osf.io',
            'social_twitter': 'socarxiv',
            'social_facebook': 'socarxiv',
            'social_instagram': 'socarxiv',
            'licenses_acceptable': [],
            'header_text': '',
            'subjects_acceptable': [],
        },
    ]

    init_app(routes=False)
    with TokuTransaction():
        for provider_data in PREPRINT_PROVIDERS:
            update_or_create(provider_data)


if __name__ == '__main__':
    main()
