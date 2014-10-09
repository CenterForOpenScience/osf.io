#!/usr/bin/env python
# encoding: utf-8
import sys
from modularodm.exceptions import ModularOdmException
from website.project.views.email import Conference
from website.app import init_app

def main():
    init_app(set_backends=True, routes=False)
    populate_conferences()

MEETING_DATA = {
    'spsp2014': {
        'name': 'SPSP 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': None,
        'public_projects': True,
    },
    'asb2014': {
        'name': 'ASB 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'logo_url': None,
        'active': False,
        'admins': None,
        'public_projects': True,
    },
    'aps2014': {
        'name': 'APS 2014',
        'info_url': 'http://centerforopenscience.org/aps/',
        'logo_url': '/static/img/2014_Convention_banner-with-APS_700px.jpg',
        'active': False,
        'admins': None,
        'public_projects': True,
    },
    'annopeer2014': {
        'name': '#annopeer',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': None,
        'public_projects': True,
    },
    'cpa2014': {
        'name': 'CPA 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': None,
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
            'Dkim@nrao.edu',
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
    for key, val in MEETING_DATA.iteritems():
        try:
            conf = Conference(
                endpoint=key, **val
            )
            conf.save()
        except ModularOdmException:
            print('{0} Conference already exists. Skipping...'.format(key))


if __name__ == '__main__':
    main()
