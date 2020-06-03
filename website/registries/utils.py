REG_CAMPAIGNS = {
    'prereg': 'OSF Preregistration',
    'osf-registered-reports': 'Registered Report Protocol Preregistration',
}

def get_campaign_schema(campaign):
    from osf.models import RegistrationSchema
    if campaign not in REG_CAMPAIGNS:
        raise ValueError('campaign must be one of: {}'.format(', '.join(REG_CAMPAIGNS.keys())))
    schema_name = REG_CAMPAIGNS[campaign]

    return RegistrationSchema.objects.filter(name=schema_name).order_by('-schema_version').first()

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
