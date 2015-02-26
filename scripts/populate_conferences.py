#!/usr/bin/env python
# encoding: utf-8

import os
import sys

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth.core import User

from website import settings
from website.app import init_app
from website.conferences.model import Conference


def main():
    init_app(set_backends=True, routes=False)
    populate_conferences()


MEETING_DATA = {
    'spsp2014': {
        'name': 'SPSP 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'asb2014': {
        'name': 'ASB 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'aps2014': {
        'name': 'APS 2014',
        'info_url': 'http://centerforopenscience.org/aps/',
        'logo_url': '/static/img/2014_Convention_banner-with-APS_700px.jpg',
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'annopeer2014': {
        'name': '#annopeer',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'cpa2014': {
        'name': 'CPA 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'filaments2014': {
        'name': 'Filaments 2014',
        'info_url': None,
        'logo_url': 'https://science.nrao.edu/science/meetings/2014/'
                    'filamentary-structure/images/filaments2014_660x178.png',
        'active': False,
        'admins': [
            'lvonschi@nrao.edu',
            'sara.d.bowman@gmail.com',
            # 'Dkim@nrao.edu',
        ],
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
        'admins': [
            'gkroll@berkeley.edu',
            'andrew@cos.io',
            'awais@berkeley.edu',
        ],
        'public_projects': True,
    },
    'spsp2015': {
        'name': 'SPSP 2015',
        'info_url': None,
        'logo_url': 'http://spspmeeting.org/CMSPages/SPSPimages/spsp2015banner.jpg',
        'active': True,
        'admins': [
            'meetings@spsp.org',
            'andrew@cos.io',
        ],
    },
    'aps2015': {
        'name': 'APS 2015',
        'info_url': None,
        'logo_url': 'http://www.psychologicalscience.org/images/APS_2015_Banner_990x157.jpg',
        'active': True,
        'admins': [
            'KatyCain526@gmail.com',
        ],
        'public_projects': True,
    },
    'icps2015': {
        'name': 'ICPS 2015',
        'info_url': None,
        'logo_url': 'http://icps.psychologicalscience.org/wp-content/themes/deepblue/images/ICPS_Website-header_990px.jpg',
        'active': True,
        'admins': [
            'KatyCain526@gmail.com',
        ],
        'public_projects': True,
    },
    'mpa2015': {
        'name': 'MPA 2015',
        'info_url': None,
        'logo_url': 'http://www.midwesternpsych.org/resources/Pictures/MPA%20logo.jpg',
        'active': True,
        'admins': [
            'mpa@kent.edu',
            'KatyCain526@gmail.com',
        ],
        'public_projects': True,
    },
    'NCCC2015': {
        'name': '2015 NC Cognition Conference',
        'info_url': None,
        'logo_url': None,
        'active': True,
        'admins': [
            'aoverman@elon.edu',
            'KatyCain526@gmail.com',
        ],
        'public_projects': True,
    },
    'VPRSF2015': {
        'name': 'Virginia Piedmont Regional Science Fair',
        'info_url': None,
        'logo_url': 'http://vprsf.org/wp-content/themes/VPRSF/images/logo.png',
        'active': True,
        'admins': [
            'director@vprsf.org',
            'KatyCain526@gmail.com',
        ],
        'public_projects': True,
    },
}


def populate_conferences():
    for meeting, attrs in MEETING_DATA.iteritems():
        admin_emails = attrs.pop('admins')
        admin_objs = []
        for email in admin_emails:
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
