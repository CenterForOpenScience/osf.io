"""Back-end code to support the Prereg Challenge initiative

Keeping the code together in this file should make it easier to remove the
features added to the OSF specifically to support this initiative in the future.

Other resources that are a part of the Prereg Challenge:

* website/static/js/pages/prereg-landing-page.js
* website/static/css/prereg.css
"""
from flask import request

from framework.auth import decorators
from framework.utils import iso8601format
from website.prereg import utils

@decorators.must_be_logged_in
def prereg_landing_page(auth, **kwargs):
    """Landing page for the prereg challenge"""
    campaign = request.path.strip('/')
    registerable_nodes = [
        node for node
        in auth.user.contributor_to
        if node.has_permission(user=auth.user, permission='admin')
    ]
    has_projects = bool(registerable_nodes)
    has_draft_registrations = bool(utils.drafts_for_user(auth.user, campaign).count())

    return {
        'has_draft_registrations': has_draft_registrations,
        'has_projects': has_projects,
        'campaign_long': utils.PREREG_CAMPAIGNS[campaign],
        'campaign_short': campaign
    }

@decorators.must_be_logged_in
def prereg_draft_registrations(auth, **kwargs):
    """API endpoint; returns prereg draft registrations the user can resume"""
    campaign = kwargs.get('campaign', 'prereg')
    drafts = utils.drafts_for_user(auth.user, campaign)
    return {
        'draftRegistrations': [
            {
                'dateUpdated': iso8601format(draft.datetime_updated),
                'dateInitiated': iso8601format(draft.datetime_initiated),
                'node': {
                    'title': draft.branched_from.title,
                },
                'initiator': {
                    'name': draft.initiator.fullname,
                },
                'url': draft.branched_from.web_url_for(
                    'edit_draft_registration_page',
                    draft_id=draft._id,
                ),
            }
            for draft in drafts
        ],
    }
