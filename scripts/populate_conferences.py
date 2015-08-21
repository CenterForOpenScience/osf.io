#!/usr/bin/env python
# encoding: utf-8

import os

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
        'name': 'Society for Personality and Social Psychology 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'asb2014': {
        'name': 'Association of Southeastern Biologists 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'aps2014': {
        'name': 'Association for Psychological Science 2014',
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
        'name': 'Canadian Psychological Association 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'filaments2014': {
        'name': 'National Radio Astronomy Observatory Filaments 2014',
        'info_url': None,
        'logo_url': 'https://science.nrao.edu/science/meetings/2014/'
                    'filamentary-structure/images/filaments2014_660x178.png',
        'active': False,
        'admins': [
            'lvonschi@nrao.edu',
            # 'Dkim@nrao.edu',
        ],
        'public_projects': True,
    },
    'bitss2014': {
        'name': 'Berkeley Initiative for Transparency in the Social Sciences Research Transparency Forum 2014',
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
            'awais@berkeley.edu',
        ],
        'public_projects': True,
    },
    'spsp2015': {
        'name': 'Society for Personality and Social Psychology 2015',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [
            'meetings@spsp.org',
        ],
    },
    'aps2015': {
        'name': 'Association for Psychological Science 2015',
        'info_url': None,
        'logo_url': 'http://www.psychologicalscience.org/images/APS_2015_Banner_990x157.jpg',
        'active': True,
        'admins': [
        ],
        'public_projects': True,
    },
    'icps2015': {
        'name': 'International Convention of Psychological Science 2015',
        'info_url': None,
        'logo_url': 'http://icps.psychologicalscience.org/wp-content/themes/deepblue/images/ICPS_Website-header_990px.jpg',
        'active': False,
        'admins': [
        ],
        'public_projects': True,
    },
    'mpa2015': {
        'name': 'Midwestern Psychological Association 2015',
        'info_url': None,
        'logo_url': 'http://www.midwesternpsych.org/resources/Pictures/MPA%20logo.jpg',
        'active': True,
        'admins': [
            'mpa@kent.edu',
        ],
        'public_projects': True,
    },
    'NCCC2015': {
        'name': 'North Carolina Cognition Conference 2015',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [
            'aoverman@elon.edu',
        ],
        'public_projects': True,
    },
    'VPRSF2015': {
        'name': 'Virginia Piedmont Regional Science Fair 2015',
        'info_url': None,
        'logo_url': 'http://vprsf.org/wp-content/themes/VPRSF/images/logo.png',
        'active': False,
        'admins': [
            'director@vprsf.org',
        ],
        'public_projects': True,
    },
    'APRS2015': {
        'name': 'UVA Annual Postdoctoral Research Symposium 2015',
        'info_url': None,
        'logo_url': 'http://s1.postimg.org/50qj9u6i7/GPA_Logo.jpg',
        'active': False,
        'admins': [
            'mhurst@virginia.edu',
        ],
        'public_projects': True,
    },
    'ASB2015': {
        'name': 'Association of Southeastern Biologists 2015',
        'info_url': None,
        'logo_url': 'http://www.sebiologists.org/wp/wp-content/uploads/2014/09/banner_image_Large.png',
        'active': False,
        'admins': [
            'amorris.mtsu@gmail.com',
        ],
        'public_projects': True,
    },
    'TeaP2015': {
        'name': 'Tagung experimentell arbeitender Psychologen 2015',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admins': [
        ],
        'public_projects': True,
    },
    'VSSEF2015': {
        'name': 'Virginia State Science and Engineering Fair 2015',
        'info_url': 'http://www.vmi.edu/conferences/vssef/vssef_home/',
        'logo_url': 'http://www.vmi.edu/uploadedImages/Images/Headers/vssef4.jpg',
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'RMPA2015': {
        'name': 'Rocky Mountain Psychological Association 2015',
        'info_url': 'http://www.rockymountainpsych.org/uploads/7/4/2/6/7426961/85th_annual_rmpa_conference_program_hr.pdf',
        'logo_url': 'http://www.rockymountainpsych.org/uploads/7/4/2/6/7426961/header_images/1397234084.jpg',
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'ARP2015': {
        'name': 'Association for Research in Personality 2015',
        'info_url': 'http://www.personality-arp.org/conference/',
        'logo_url': 'http://www.personality-arp.org/wp-content/uploads/conference/st-louis-arp.jpg',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'SEP2015': {
        'name': 'Society of Experimental Psychologists Meeting 2015',
        'info_url': 'http://faculty.virginia.edu/Society_of_Experimental_Psychologists/',
        'logo_url': 'http://www.sepsych.org/nav/images/SEP-header.gif',
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'Reid2015': {
        'name': 'L. Starling Reid Undergraduate Psychology Conference 2015',
        'info_url': 'http://avillage.web.virginia.edu/Psych/Conference',
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'NEEPS2015': {
        'name': 'Northeastern Evolutionary Psychology Conference 2015',
        'info_url': 'http://neeps2015.weebly.com/',
        'logo_url': None,
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'VaACS2015': {
        'name': 'Virginia Section American Chemical Society Student Poster Session 2015',
        'info_url': 'http://virginia.sites.acs.org/',
        'logo_url': 'http://virginia.sites.acs.org/Bulletin/15/UVA.jpg',
        'active': False,
        'admins': [],
        'public_projects': True,
    },
    'MADSSCi2015': {
        'name': 'Mid-Atlantic Directors and Staff of Scientific Cores & Southeastern Association of Shared Services 2015',
        'info_url': 'http://madssci.abrf.org',
        'logo_url': 'http://s24.postimg.org/qtc3baefp/2015madssci_seasr.png',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'NRAO2015': {
        'name': 'National Radio Astronomy Observatory Accretion 2015',
        'info_url': 'https://science.nrao.edu/science/meetings/2015/accretion2015/posters',
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'ARCS2015': {
        'name': 'Advancing Research Communication and Scholarship 2015',
        'info_url': 'http://commons.pacificu.edu/arcs/',
        'logo_url': 'http://commons.pacificu.edu/assets/md5images/4dfd167454e9f4745360a9550e189323.png',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'singlecasedesigns2015': {
        'name': 'Single Case Designs in Clinical Psychology: Uniting Research and Practice',
        'info_url': 'https://www.royalholloway.ac.uk/psychology/events/eventsarticles/singlecasedesignsinclinicalpsychologyunitingresearchandpractice.aspx',
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'OSFM2015': {
        'name': 'OSF for Meetings 2015',
        'info_url': None,
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'JSSP2015': {
        'name': 'Japanese Society of Social Psychology 2015',
        'info_url': 'http://www.socialpsychology.jp/conf2015/index.html',
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    '4S2015': {
        'name': 'Society for Social Studies of Science 2015',
        'info_url': 'http://www.4sonline.org/meeting',
        'logo_url': 'http://www.4sonline.org/ee/denver-skyline.jpg',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'IARR2016': {
        'name': 'International Association for Relationship Research 2016',
        'info_url': 'http://iarr.psych.utoronto.ca/',
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'IA2015': {
        'name': 'Inclusive Astronomy 2015',
        'info_url': 'https://vanderbilt.irisregistration.com/Home/Site?code=InclusiveAstronomy2015',
        'logo_url': 'https://vanderbilt.blob.core.windows.net/images/Inclusive%20Astronomy.jpg',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'PsiChiRepository': {
        'name': 'Psi Chi Repository',
        'info_url': None,
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'R2RC': {
        'name': 'Right to Research Coalition',
        'info_url': None,
        'logo_url': None,
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'OpenCon2015': {
        'name': 'OpenCon2015',
        'info_url': 'http://opencon2015.org/',
        'logo_url': 'http://s8.postimg.org/w9b30pxyd/Open_Con2015_new_logo.png',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'ESIP2015': {
        'name': 'Earth Science Information Partners 2015',
        'info_url': 'http://esipfed.org/',
        'logo_url': 'http://s30.postimg.org/m2uz2g4pt/ESIP.png',
        'active': True,
        'admins': [],
        'public_projects': True,
    },
    'SPSP2016': {
        'name': 'Society for Personality and Social Psychology 2016',
        'info_url': 'http://meeting.spsp.org/',
        'logo_url': 'http://meeting.spsp.org/sites/default/files/2016ConventionLogo.png',
        'active': True,
        'admins': [],
        'public_projects': True,
}


def populate_conferences():
    for meeting, attrs in MEETING_DATA.iteritems():
        meeting = meeting.strip()
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
            changed_fields = conf.save()
            if changed_fields:
                print('Changed: {}'.format(changed_fields))
        else:
            print('Added new Conference: {}'.format(meeting))


if __name__ == '__main__':
    main()
