REG_CAMPAIGNS = {
    'prereg_challenge': 'Prereg Challenge',
    'prereg': 'OSF Preregistration',
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
    if campaign:
        return DraftRegistration.objects.filter(
            registration_schema=get_campaign_schema(campaign),
            approval=None,
            registered_node=None,
            deleted__isnull=True,
            branched_from__in=Node.objects.filter(
                is_deleted=False,
                contributor__admin=True,
                contributor__user=user).values_list('id', flat=True)
        )
    else:
        return DraftRegistration.objects.filter(
            approval=None,
            registered_node=None,
            deleted__isnull=True,
            branched_from__in=Node.objects.filter(
                is_deleted=False,
                contributor__admin=True,
                contributor__user=user).values_list('id', flat=True)
        )
