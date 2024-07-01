from enum import Enum

def get_entry_point(user):
    """
    Given the user system_tags, return the user entry point (osf, osf4m, institution)
    In case of multiple entry_points existing in the system_tags, return only the first one.
    """
    entry_points = [
        CampaignSourceTags.Osf4m.value,
        'institution_campaign',
        provider_source_tag('osf', 'preprint'),
    ]
    for i in user.system_tags:
        if i in entry_points:
            return i
    else:
        return 'osf'


def provider_source_tag(provider_id, service=None):
    if service:
        return f'source:provider|{service}|{provider_id}'
    else:
        return f'source:provider|{provider_id}'


def campaign_source_tag(campaign_name):
    return f'source:campaign|{campaign_name}'


def provider_claimed_tag(provider_id, service=None):
    if service:
        return f'claimed:provider|{service}|{provider_id}'
    else:
        return f'claimed:provider|{provider_id}'


def campaign_claimed_tag(campaign_name):
    return f'claimed:campaign|{campaign_name}'


class OsfSourceTags(Enum):
    Osf = provider_source_tag('osf')


# Needs to be updated when new campaigns are added.
class CampaignSourceTags(Enum):
    ErpChallenge = campaign_source_tag('erp_challenge')
    OsfRegisteredReports = campaign_source_tag('osf_registered_reports')
    Osf4m = campaign_source_tag('osf4m')
    AguConference2023 = campaign_source_tag('agu_conference_2023')


class OsfClaimedTags(Enum):
    Osf = provider_claimed_tag('osf')


# Needs to be updated when new campaigns are added.
class CampaignClaimedTags(Enum):
    ErpChallenge = campaign_claimed_tag('erp_challenge')
    OsfRegisteredReports = campaign_claimed_tag('osf_registered_reports')
    Osf4m = campaign_claimed_tag('osf4m')
