import furl

from werkzeug.datastructures import ImmutableDict

from website import mails
from website.settings import DOMAIN

CAMPAIGNS = {
    'prereg': {
        'system_tag': 'prereg_challenge_campaign',
        'redirect_url': furl.furl(DOMAIN).add(path='prereg/').url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREREG,
    },
    'institution': {
        'system_tag': 'institution_campaign',
        'redirect_url': ''
    },
    'erpc': {
        'system_tag': 'erp_challenge_campaign',
        'redirect_url': furl.furl(DOMAIN).add(path='erpc/').url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_ERPC,
    },
    # Various preprint services
    # Each preprint service will offer their own campaign with appropriate distinct branding
    'osf-preprints': {
        'system_tag': 'osf_preprints',
        'redirect_url': furl.furl(DOMAIN).add(path='preprints/').url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREPRINTS('osf', 'OSF'),
        'proxy_login': True,
        'branded': False,
        'provider': 'OSF'
    },
}

providers = [
    'SocArXiv',
    'engrXiv',
    'PsyArXiv'
]

for provider in providers:
    provider_id = provider.lower()
    key = '{}-preprints'.format(provider_id)
    tag = '{}_preprints'.format(provider_id)
    path = 'preprints/{}'.format(provider_id)
    CAMPAIGNS[key] = {
        'system_tag': tag,
        'redirect_url': furl.furl(DOMAIN).add(path=path).url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREPRINTS('branded', provider),
        'proxy_login': True,
        'branded': True,
        'provider': provider,
    }

CAMPAIGNS = ImmutableDict(CAMPAIGNS)


def system_tag_for_campaign(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign].get('system_tag')
    return None


def email_template_for_campaign(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign].get('confirmation_email_template')
    return None


def campaign_for_user(user):
    for campaign, config in CAMPAIGNS.items():
        if config['system_tag'] in user.system_tags:
            return campaign
    return None


def is_proxy_login(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign].get('proxy_login')
    return None


def is_branded_service(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign].get('branded')
    return None


def get_service_provider(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign].get('provider')
    return None


def campaign_url_for(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign].get('redirect_url')
    return None
