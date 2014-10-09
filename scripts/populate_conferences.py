from website.project.views.email import Conference

MEETING_DATA = {
    'spsp2014': {
        'name': 'SPSP 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admin': None,
        'public_projects': True,
    },
    'asb2014': {
        'name': 'ASB 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'logo_url': None,
        'active': False,
        'admin': None,
        'public_projects': True,
    },
    'aps2014': {
        'name': 'APS 2014',
        'info_url': 'http://centerforopenscience.org/aps/',
        'logo_url': '/static/img/2014_Convention_banner-with-APS_700px.jpg',
        'active': False,
        'admin': None,
        'public_projects': True,
    },
    'annopeer2014': {
        'name': '#annopeer',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admin': None,
        'public_projects': True,
    },
    'cpa2014': {
        'name': 'CPA 2014',
        'info_url': None,
        'logo_url': None,
        'active': False,
        'admin': None,
        'public_projects': True,
    },
    'filaments2014': {
        'name': 'Filaments 2014',
        'info_url': None,
        'logo_url': 'https://science.nrao.edu/science/meetings/2014/'
                    'filamentary-structure/images/filaments2014_660x178.png',
        'active': True,
        'admin': None,
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
        conf = Conference(
            endpoint=key,
            name=val['name'],
            info_url=val['info_url'],
            logo_url=val['logo_url'],
            active=val['active'],
            admin=val['admin'],
            public_projects=val['public_projects'],
        )
        conf.save()