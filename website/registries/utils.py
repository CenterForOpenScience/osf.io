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
    if not user or user.is_anonymous:
        return None

    drafts = user.draft_registrations_active

    if campaign:
        drafts = drafts.filter(
            registration_schema=get_campaign_schema(campaign),
        )

    return drafts
