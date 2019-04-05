# -*- coding: utf-8 -*-
from flask import request
from framework.auth import Auth, decorators
from framework.utils import iso8601format
from website.registries import utils


def _view_registries_landing_page(campaign=None, **kwargs):
    """Landing page for the various registrations"""
    auth = kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
    is_logged_in = kwargs['auth'].logged_in
    if is_logged_in:
        registerable_nodes = [
            node for node
            in auth.user.contributor_to
            if node.has_permission(user=auth.user, permission='admin')
        ]
        has_projects = bool(registerable_nodes)
    else:
        has_projects = False

    return {
        'is_logged_in': is_logged_in,
        'has_draft_registrations': bool(utils.drafts_for_user(auth.user, campaign)),
        'has_projects': has_projects,
        'campaign_long': utils.REG_CAMPAIGNS.get(campaign),
        'campaign_short': campaign

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
