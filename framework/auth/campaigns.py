import httplib as http

from werkzeug.datastructures import ImmutableDict
from framework.exceptions import HTTPError

from website import mails
from website.util import web_url_for

CAMPAIGNS = ImmutableDict({
    'prereg_challenge': {
        'system_tag': 'prereg_challenge_campaign',
        'redirect_url': lambda: web_url_for('prereg_landing_page'),
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREREG,
    },
})


def email_template_for_campaign(campaign, default=None):
    if campaign in CAMPAIGNS:
        try:
            return CAMPAIGNS[campaign]['confirmation_email_template']
        except KeyError as e:
            if default:
                return default
            else:
                raise e
    return default

def campaign_for_user(user):
    campaigns = [tag for tag in user.system_tags if tag in CAMPAIGNS]
    if campaigns:
        # TODO: This is a bit of a one-off to support the Prereg Challenge.
        # We should think more about the campaigns architecture and in
        # particular define the behavior if the user has more than one
        # campagin tag in their system_tags.
        return campaigns[0]

def campaign_url_for(campaign):
    if campaign not in CAMPAIGNS:
        raise HTTPError(http.BAD_REQUEST)
    else:
        return CAMPAIGNS[campaign]['redirect_url']()
