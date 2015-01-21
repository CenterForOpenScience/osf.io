#!/usr/bin/env python
# encoding: utf-8

import os
import sys

import argparse

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth.core import User

from website import settings
from website.app import init_app
from website.conferences.model import Conference


def parse_args():
    parser = argparse.ArgumentParser(description='Create conferences with a specified admin email.')
    parser.add_argument('-u', '--user', dest='user', required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    init_app(set_backends=True, routes=False)
    populate_conferences(args.user)


MEETING_DATA = {
    'spsp2014': {
        'name': 'SPSP 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'public_projects': True,
    },
    'asb2014': {
        'name': 'ASB 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'logo_url': None,
        'active': False,
        'public_projects': True,
    },
    'aps2014': {
        'name': 'APS 2014',
        'info_url': 'http://centerforopenscience.org/aps/',
        'logo_url': '/static/img/2014_Convention_banner-with-APS_700px.jpg',
        'active': False,
        'public_projects': True,
    },
    'annopeer2014': {
        'name': '#annopeer',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'public_projects': True,
    },
    'cpa2014': {
        'name': 'CPA 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'public_projects': True,
    },
    'filaments2014': {
        'name': 'Filaments 2014',
        'info_url': None,
        'logo_url': 'https://science.nrao.edu/science/meetings/2014/'
                    'filamentary-structure/images/filaments2014_660x178.png',
        'active': False,
        'public_projects': True,
    },
    'bitss2014': {
        'name': 'BITSS Research Transparency Forum 2014',
        'info_url': None,
        'logo_url': os.path.join(
            settings.STATIC_URL_PATH,
            'img',
            'conferences',
            'bitss.jpg',
        ),
        'active': False,
        'public_projects': True,
    },
    'spsp2015': {
        'name': 'SPSP 2015',
        'info_url': None,
        'logo_url': 'http://spspmeeting.org/CMSPages/SPSPimages/spsp2015banner.jpg',
        'active': True,
    },
    'aps2015': {
        'name': 'APS 2015',
        'info_url': None,
        'logo_url': 'http://www.psychologicalscience.org/images/APS_2015_Banner_990x157.jpg',
        'active': True,
        'public_projects': True,
    },
    'icps2015': {
        'name': 'ICPS 2015',
        'info_url': None,
        'logo_url': 'http://icps.psychologicalscience.org/wp-content/themes/deepblue/images/ICPS_Website-header_990px.jpg',
        'active': True,
        'public_projects': True,
    },
    'mpa2015': {
        'name': 'MPA 2015',
        'info_url': None,
        'logo_url': 'http://www.midwesternpsych.org/resources/Pictures/MPA%20logo.jpg',
        'active': True,
        'public_projects': True,
    },
    'NCCC2015': {
        'name': '2015 NC Cognition Conference',
        'info_url': None,
        'logo_url': None,
        'active': True,
        'public_projects': True,
    },
}


def populate_conferences(email):
    for meeting, attrs in MEETING_DATA.iteritems():
        admin_objs = []
        try:
            user = User.find_one(Q('username', 'iexact', email))
            admin_objs.append(user)
        except ModularOdmException:
            raise RuntimeError('Username {0!r} is not registered.'.format(email))
        conf = Conference(
            endpoint=meeting, admins=admin_objs, **attrs
        )
        try:
            conf.save()
        except ModularOdmException:
            print('{0} Conference already exists. Updating existing record...'.format(meeting))
            conf = Conference.find_one(Q('endpoint', 'eq', meeting))
            for key, value in attrs.items():
                setattr(conf, key, value)
            conf.admins = admin_objs
            conf.save()


if __name__ == '__main__':
    main()
