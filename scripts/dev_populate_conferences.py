#!/usr/bin/env python
# encoding: utf-8

import os

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from website import settings
from website.app import init_app
from website.conferences.model import Conference


def main():
    init_app(set_backends=True, routes=False)
    populate_conferences()


MEETING_DATA = {
    'spsp2014': {
        'name': 'Society for Personality and Social Psychology 2014',
        'info_url': None,
        'logo_url': None,
        'location': 'Washington DC',
        "start_date": "Feb 10 2015"
        'end_date': "Feb 12 2015",
        'active': False,
        'admins': [],
        'public_projects': True,
        'poster': True,
        'talk': True,
    },
    'asb2014': {
        'name': 'Association of Southeastern Biologists 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'logo_url': None,
        'location': 'New York',
        'conference_date': None,
        'active': False,
        'admins': [],
        'public_projects': True,
        'poster': True,
        'talk': True,
    },
    'aps2014': {
        'name': 'Association for Psychological Science 2014',
        'info_url': 'http://centerforopenscience.org/aps/',
        'logo_url': '/static/img/2014_Convention_banner-with-APS_700px.jpg',
        'location': 'New York',
        'conference_date': None,
        'active': False,
        'admins': [],
        'public_projects': True,
        'poster': True,
        'talk': True,
    },
    'annopeer2014': {
        'name': '#annopeer',
        'info_url': None,
        'logo_url': None,
        'location': 'New York',
        'conference_date': None,
        'active': False,
        'admins': [],
        'public_projects': True,
        'poster': True,
        'talk': True,
    },
}

def clear_up_conf():
    print "Clear all the existing conferences"
    confs = Conference.find()
    for conf in confs:
        print conf.to_storage()
        conf.remove()
        conf.save()

def populate_conferences():
    clear_up_conf()
    for meeting, attrs in MEETING_DATA.iteritems():
        conf = Conference(
            endpoint=meeting, **attrs
        )
        try:
            conf.save()
        except ModularOdmException:
            print('{0} Conference already exists. Updating existing record...'.format(meeting))
            conf = Conference.find_one(Q('endpoint', 'eq', meeting))
            for key, value in attrs.items():
                setattr(conf, key, value)
            conf.save()


if __name__ == '__main__':
    main()
