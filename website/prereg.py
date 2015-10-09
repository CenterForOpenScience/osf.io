"""Back-end code to support the Prereg Challenge initiative

Keeping the code together in this file should make it easier to remove the
features added to the OSF specifically to support this initiative in the future.

Other resources that are a part of the Prereg Challenge:

* website/static/js/pages/prereg-landing-page.js
* website/static/css/prereg.css
"""
from modularodm import Q

from framework.auth import decorators
from framework.utils import iso8601format
from website import models


@decorators.must_be_logged_in
def prereg_landing_page(auth, **kwargs):
    """Landing page for the prereg challenge"""
    has_project = False
    has_draft_registration = False

    registerable_nodes = (
        node for node
        in auth.user.contributor_to
        if node.has_permission(user=auth.user, permission='admin')
    )

    for node in registerable_nodes:
        if not has_project:
            has_project = True
        if node.draft_registrations:
            has_draft_registration = True
            break

    return {
        'has_draft_registration': has_draft_registration,
        'has_project': has_project,
    }


@decorators.must_be_logged_in
def prereg_draft_registrations(auth, **kwargs):
    """API endpoint; returns prereg draft registrations the user can resume"""
    PREREG_CHALLENGE_METASCHEMA = models.MetaSchema.find_one(
        Q('name', 'eq', 'Open-Ended Registration') &
        Q('schema_version', 'eq', 2)
    )

    drafts = models.DraftRegistration.find(
        Q('registration_schema', 'eq', PREREG_CHALLENGE_METASCHEMA)
    )

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
