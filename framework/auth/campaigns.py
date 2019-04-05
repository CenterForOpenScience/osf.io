import furl
import threading

from django.utils import timezone

from website import mails, settings
from osf.models import PreprintProvider
from website.settings import DOMAIN, CAMPAIGN_REFRESH_THRESHOLD
from framework.utils import throttle_period_expired


mutex = threading.Lock()
CAMPAIGNS = None
CAMPAIGNS_LAST_REFRESHED = timezone.now()


def get_campaigns():

    global CAMPAIGNS
    global CAMPAIGNS_LAST_REFRESHED

    if not CAMPAIGNS or (not mutex.locked() and throttle_period_expired(CAMPAIGNS_LAST_REFRESHED, CAMPAIGN_REFRESH_THRESHOLD)):
        with mutex:
            # Native campaigns: PREREG and ERPC
            newest_campaigns = {
                'prereg': {
                    'system_tag': 'source:campaign|prereg',
                    'redirect_url': furl.furl(DOMAIN).add(path='prereg/').url,
                    'confirmation_email_template': mails.CONFIRM_EMAIL_PREREG,
                    'login_type': 'native',
                    'logo': settings.OSF_PREREG_LOGO
                },
                'erpc': {
                    'system_tag': 'source:campaign|erp',
                    'redirect_url': furl.furl(DOMAIN).add(path='erpc/').url,
                    'confirmation_email_template': mails.CONFIRM_EMAIL_ERPC,
                    'login_type': 'native',
                },
            }

            # Institution Login
            newest_campaigns.update({
                'institution': {
                    'system_tag': 'institution_campaign',
                    'redirect_url': '',
                    'login_type': 'institution',
                },
            })

            # Proxy campaigns: Preprints, both OSF and branded ones
            preprint_providers = PreprintProvider.objects.all()
            for provider in preprint_providers:
                if provider._id == 'osf':
                    template = 'osf'
                    name = 'OSF'
                    url_path = 'preprints/'
                    external_url = None
                else:
                    template = 'branded'
                    name = provider.name
                    url_path = 'preprints/{}'.format(provider._id)
                    external_url = provider.domain
                campaign = '{}-preprints'.format(provider._id)
                system_tag = 'source:provider|preprint|{}'.format(provider._id)
                newest_campaigns.update({
                    campaign: {
                        'system_tag': system_tag,
                        'redirect_url': furl.furl(DOMAIN).add(path=url_path).url,
                        'external_url': external_url,
                        'confirmation_email_template': mails.CONFIRM_EMAIL_PREPRINTS(template, name),
                        'login_type': 'proxy',
                        'provider': name,
                        'logo': provider._id if name != 'OSF' else settings.OSF_PREPRINTS_LOGO,
                    }
                })

            # Proxy campaigns: Registries, OSF only
            # TODO: refactor for futher branded registries when there is a model for registries providers
            newest_campaigns.update({
                'osf-registries': {
                    'system_tag': 'source:provider|registry|osf',
                    'redirect_url': furl.furl(DOMAIN).add(path='registries/').url,
                    'confirmation_email_template': mails.CONFIRM_EMAIL_REGISTRIES_OSF,
                    'login_type': 'proxy',
                    'provider': 'osf',
                    'logo': settings.OSF_REGISTRIES_LOGO
                }
            })

            newest_campaigns.update({
                'osf-registered-reports': {
                    'system_tag': 'source:campaign|osf_registered_reports',
                    'redirect_url': furl.furl(DOMAIN).add(path='rr/').url,
                    'confirmation_email_template': mails.CONFIRM_EMAIL_REGISTRIES_OSF,
                    'login_type': 'proxy',
                    'provider': 'osf',
                    'logo': settings.OSF_REGISTRIES_LOGO
                }
            })

            CAMPAIGNS = newest_campaigns
            CAMPAIGNS_LAST_REFRESHED = timezone.now()

    return CAMPAIGNS


def system_tag_for_campaign(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('system_tag')
    return None


def email_template_for_campaign(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('confirmation_email_template')
    return None


def campaign_for_user(user):
    campaigns = get_campaigns()
    for campaign, config in campaigns.items():
        if config.get('system_tag') in user.system_tags:
            return campaign
    return None


def is_institution_login(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('login_type') == 'institution'
    return None


def is_native_login(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('login_type') == 'native'
    return None


def is_proxy_login(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('login_type') == 'proxy'
    return None


def get_campaign_logo(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('logo', None)
    return None


def get_service_provider(campaign):
    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('provider')
    return None


def campaign_url_for(campaign):
    """
    Return the campaign's URL on OSF domain.

    :param campaign: the campaign
    :return: the url
    """

    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('redirect_url')
    return None


def external_campaign_url_for(campaign):
    """
    Return the campaign's URL on Non-OSF domain, which is available for phase 2 branded preprints only.

    :param campaign: the campaign
    :return: the external url if the campaign is hosted on Non-OSF domain, None otherwise
    """

    campaigns = get_campaigns()
    if campaign in campaigns:
        return campaigns.get(campaign).get('external_url')
    return None


def get_external_domains():
    """
    Return a list of trusted external domains for all eligible campaigns.
    """

    campaigns = get_campaigns()
    external_domains = []
    for campaign, config in campaigns.items():
        external_url = config.get('external_url', None)
        if external_url:
            external_domains.append(external_url)
    return external_domains


NODE_SOURCE_TAG_CLAIMED_TAG_RELATION = {
    'source:campaign|erp': 'claimed:campaign|erp',
    'source:campaign|prereg_challenge': 'claimed:campaign|prereg_challenge',
    'source:campaign|prereg': 'claimed:campaign|prereg',
    'source:campaign|osf_registered_reports': 'claimed:campaign|osf_registered_reports',
    'source:campaign|osf4m': 'claimed:campaign|osf4m',
    'source:provider|osf': 'claimed:provider|osf'
}
