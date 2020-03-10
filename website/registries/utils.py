REG_CAMPAIGNS = {
    'prereg_challenge': 'Prereg Challenge',
    'prereg': 'OSF Preregistration',
    'registered_report': 'Registered Report Protocol Preregistration',
}

REG_CAMPAIGNS_VERSION = {
    'prereg_challenge': 2,
    'prereg': 3,
    'registered_report': 4,
}

def get_campaign_schema(campaign):
    from osf.models import RegistrationSchema
    if campaign not in REG_CAMPAIGNS:
        raise ValueError('campaign must be one of: {}'.format(', '.join(REG_CAMPAIGNS.keys())))
    schema_name = REG_CAMPAIGNS[campaign]
    schema_version = REG_CAMPAIGNS_VERSION[campaign]

    return RegistrationSchema.objects.get(name=schema_name, schema_version=schema_version)

def drafts_for_user(user, campaign=None):
    from osf.models import DraftRegistration, Node
    from osf.utils.permissions import ADMIN_NODE

    if not user or user.is_anonymous:
        return None

    node_qs = Node.objects.get_nodes_for_user(user, ADMIN_NODE).values_list('id', flat=True)
    drafts = DraftRegistration.objects.filter(
        approval=None,
        registered_node=None,
        deleted__isnull=True,
        branched_from__in=node_qs,
    )

    if campaign:
        drafts = drafts.filter(
            registration_schema=get_campaign_schema(campaign),
        )

    return drafts
