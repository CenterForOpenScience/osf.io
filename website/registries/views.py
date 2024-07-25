from framework.auth import decorators
from framework.utils import iso8601format
from website.registries import utils


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
