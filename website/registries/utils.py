REG_CAMPAIGNS = {
    'prereg': 'Prereg Challenge',
    'registered_report': 'Registered Report Protocol Preregistration',
}

def get_campaign_schema(campaign):
    from osf.models import RegistrationSchema
    if campaign not in REG_CAMPAIGNS:
        raise ValueError('campaign must be one of: {}'.format(', '.join(REG_CAMPAIGNS.keys())))
    schema_name = REG_CAMPAIGNS[campaign]

    return RegistrationSchema.objects.get(name=schema_name, schema_version=2)

def drafts_for_user(user, campaign=None):
    from osf.models import DraftRegistration, Node
    from guardian.shortcuts import get_objects_for_user

    if not user or user.is_anonymous:
        return None

    node_qs = get_objects_for_user(user, 'admin_node', Node, with_superuser=False).exclude(is_deleted=True).values_list('id', flat=True)

    drafts = DraftRegistration.objects.filter(
        approval=None,
        registered_node=None,
        deleted__isnull=True,
        branched_from__in=node_qs,
        initiator=user
    )

    if campaign:
        drafts = drafts.filter(
            registration_schema=get_campaign_schema(campaign),
        )

    return drafts
