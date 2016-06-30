from modularodm import Q

from website.util import permissions


PREREG_CAMPAIGNS = {
    'prereg': 'Prereg Challenge',
    'erpc': 'Election Research Preacceptance Challenge',
}

def drafts_for_user(user, campaign):
    from website import models  # noqa

    user_projects = models.Node.find(
        Q('is_deleted', 'eq', False) &
        Q('permissions.{0}'.format(user._id), 'in', [permissions.ADMIN])
    )
    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema(campaign)
    return models.DraftRegistration.find(
        Q('registration_schema', 'eq', PREREG_CHALLENGE_METASCHEMA) &
        Q('approval', 'eq', None) &
        Q('registered_node', 'eq', None) &
        Q('branched_from', 'in', [p._id for p in user_projects])
    )

def get_prereg_schema(campaign='prereg'):
    from website.models import MetaSchema  # noqa
    if campaign not in PREREG_CAMPAIGNS:
        raise ValueError('campaign must be one of: {}'.format(', '.join(PREREG_CAMPAIGNS.keys())))
    schema_name = PREREG_CAMPAIGNS[campaign]

    return MetaSchema.find_one(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', 2)
    )
