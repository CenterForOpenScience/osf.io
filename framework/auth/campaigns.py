import httplib as http

from werkzeug.datastructures import ImmutableDict
from framework.exceptions import HTTPError

from website import mails
from website.util import web_url_for

CAMPAIGNS = ImmutableDict({
    'prereg': {
        'system_tag': 'prereg_challenge_campaign',
        'redirect_url': lambda: web_url_for('prereg_landing_page'),
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREREG,
    },
    'institution': {
        'system_tag': 'institution_campaign',
        'redirect_url': lambda: ''
    }})


def system_tag_for_campaign(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign]['system_tag']
    return None


def email_template_for_campaign(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign]['confirmation_email_template']


def campaign_for_user(user):
    for campaign, config in CAMPAIGNS.items():
        # TODO: This is a bit of a one-off to support the Prereg Challenge.
        # We should think more about the campaigns architecture and in
        # particular define the behavior if the user has more than one
        # campagin tag in their system_tags.
        if config['system_tag'] in user.system_tags:
            return campaign


def campaign_url_for(campaign):
    if campaign not in CAMPAIGNS:
        raise HTTPError(http.BAD_REQUEST)
    else:
        return CAMPAIGNS[campaign]['redirect_url']()
