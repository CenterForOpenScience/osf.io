import httplib as http

from framework.exceptions import HTTPError

from website import mails
from website.util import web_url_for

VALID_CAMPAIGNS = (
    'prereg',
)

EMAIL_TEMPLATE_MAP = {
    'prereg': mails.CONFIRM_EMAIL_PREREG
}

def email_template_for_campaign(campaign, default=None):
    if campaign in VALID_CAMPAIGNS:
        try:
            return EMAIL_TEMPLATE_MAP[campaign]
        except KeyError as e:
            if default:
                return default
            else:
                raise e
    return default

def campaign_for_user(user):
    campaigns = [tag for tag in user.system_tags if tag in VALID_CAMPAIGNS]
    if campaigns:
        # TODO: This is a bit of a one-off to support the Prereg Challenge.
        # We should think more about the campaigns architecture and in
        # particular define the behavior if the user has more than one
        # campagin tag in their system_tags.
        return campaigns[0]

def campaign_url_for(campaign):
    # Defined inside this function to ensure a request context
    REDIRECT_MAP = {
        'prereg': web_url_for('prereg_landing_page')
    }
    if campaign not in VALID_CAMPAIGNS:
        raise HTTPError(http.BAD_REQUEST)
    else:
        try:
            return REDIRECT_MAP[campaign]
        except KeyError:
            raise HTTPError(http.NOT_FOUND)
