# -*- coding: utf-8 -*-
from flask import request
from framework.auth import Auth, decorators
from framework.utils import iso8601format
from osf.utils.permissions import ADMIN
from website.registries import utils
from website import util

def _view_registries_landing_page(campaign=None, **kwargs):
    """Landing page for the various registrations"""
    auth = kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
    is_logged_in = kwargs['auth'].logged_in
    if is_logged_in:
        # Using contributor_to instead of contributor_to_or_group_member.
        # You need to be an admin contributor to register a node
        registerable_nodes = [
            node for node
            in auth.user.contributor_to
            if node.has_permission(user=auth.user, permission=ADMIN)
        ]
        has_projects = bool(registerable_nodes)
    else:
        has_projects = False

    if campaign == 'osf-registered-reports':
        campaign_url_param = 'osf-registered-reports'
    elif campaign == 'prereg':
        campaign_url_param = 'prereg'
    else:
        campaign_url_param = ''

    return {
        'is_logged_in': is_logged_in,
        'has_draft_registrations': bool(utils.drafts_for_user(auth.user, campaign)),
        'has_projects': has_projects,
        'campaign_long': utils.REG_CAMPAIGNS.get(campaign),
        'campaign_short': campaign,
        'sign_up_url': util.web_url_for('auth_register', _absolute=True, campaign=campaign_url_param, next=request.url),
    }


def registered_reports_landing(**kwargs):
    return _view_registries_landing_page('osf-registered-reports', **kwargs)


@decorators.must_be_logged_in
def draft_registrations(auth, **kwargs):
    """API endpoint; returns various draft registrations the user can resume their draft"""
    campaign = kwargs.get('campaign', None)
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


def registries_landing_page(**kwargs):
    # placeholder for developer who don't have ember app set up.
    return {}
