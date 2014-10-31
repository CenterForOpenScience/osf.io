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
        'active': True,
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
        'active': True,
        'admins': [
            'gkroll@berkeley.edu',
            'andrew@cos.io',
        ],
        'public_projects': True,
    },
    # TODO: Uncomment on 2015/02/01
    # 'spsp2015': {
    #     'name': 'SPSP 2015',
    #     'info_url': None,
    #     'logo_url': None,
    #     'active': False,
    # },
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
        try:
            conf = Conference(
                endpoint=meeting, admins=admin_objs, **attrs
            )
            conf.save()
        except ModularOdmException:
            print('{0} Conference already exists. Skipping...'.format(meeting))


if __name__ == '__main__':
    main()
