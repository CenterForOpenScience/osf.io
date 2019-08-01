# -*- coding: utf-8 -*-
from enum import Enum

def get_entry_point(user):
    """
    Given the user system_tags, return the user entry point (osf, osf4m, prereg, institution)
    In case of multiple entry_points existing in the system_tags, return only the first one.
    """
    entry_points = [
        CampaignSourceTags.Osf4m.value,
        CampaignSourceTags.PreregChallenge.value,
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
        return 'source:provider|{}|{}'.format(service, provider_id)
    else:
        return 'source:provider|{}'.format(provider_id)


def campaign_source_tag(campaign_name):
    return 'source:campaign|{}'.format(campaign_name)


def provider_claimed_tag(provider_id, service=None):
    if service:
        return 'claimed:provider|{}|{}'.format(service, provider_id)
    else:
        return 'claimed:provider|{}'.format(provider_id)


def campaign_claimed_tag(campaign_name):
    return 'claimed:campaign|{}'.format(campaign_name)


class OsfSourceTags(Enum):
    Osf = provider_source_tag('osf')


# Needs to be updated when new campaigns are added.
class CampaignSourceTags(Enum):
    ErpChallenge = campaign_source_tag('erp_challenge')
    PreregChallenge = campaign_source_tag('prereg_challenge')
    Prereg = campaign_source_tag('prereg')
    OsfRegisteredReports = campaign_source_tag('osf_registered_reports')
    Osf4m = campaign_source_tag('osf4m')


class OsfClaimedTags(Enum):
    Osf = provider_claimed_tag('osf')


# Needs to be updated when new campaigns are added.
class CampaignClaimedTags(Enum):
    ErpChallenge = campaign_claimed_tag('erp_challenge')
    PreregChallenge = campaign_claimed_tag('prereg_challenge')
    Prereg = campaign_claimed_tag('prereg')
    OsfRegisteredReports = campaign_claimed_tag('osf_registered_reports')
    Osf4m = campaign_claimed_tag('osf4m')
