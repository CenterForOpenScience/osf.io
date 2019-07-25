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
        ProviderSourceTags.OsfPreprints.value
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


# Needs to be updated when new providers are added.
class ProviderSourceTags(Enum):
    AfricarxivPreprints = provider_source_tag('africarxiv', 'preprint')
    AgrixivPreprints = provider_source_tag('agrixiv', 'preprint')
    ArabixivPreprints = provider_source_tag('arabixiv', 'preprint')
    MetaarxivPreprints = provider_source_tag('metaarxiv', 'preprint')
    EartharxivPreprints = provider_source_tag('eartharxiv', 'preprint')
    EcoevorxivPreprints = provider_source_tag('ecoevorxiv', 'preprint')
    EcsarxivPreprints = provider_source_tag('ecsarxiv', 'preprint')
    EngrxivPreprints = provider_source_tag('engrxiv', 'preprint')
    FocusarchivePreprints = provider_source_tag('focusarchive', 'preprint')
    FrenxivPreprints = provider_source_tag('frenxiv', 'preprint')
    InarxivPreprints = provider_source_tag('inarxiv', 'preprint')
    LawarxivPreprints = provider_source_tag('lawarxiv', 'preprint')
    LissaPreprints = provider_source_tag('lissa', 'preprint')
    MarxivPreprints = provider_source_tag('marxiv', 'preprint')
    MediarxivPreprints = provider_source_tag('mediarxiv', 'preprint')
    MindrxivPreprints = provider_source_tag('mindrxiv', 'preprint')
    NutrixivPreprints = provider_source_tag('nutrixiv', 'preprint')
    OsfPreprints = provider_source_tag('osf', 'preprint')
    PaleorxivPreprints = provider_source_tag('paleorxiv', 'preprint')
    PsyarxivPreprints = provider_source_tag('psyarxiv', 'preprint')
    SocarxivPreprints = provider_source_tag('socarxiv', 'preprint')
    SportrxivPreprints = provider_source_tag('sportrxiv', 'preprint')
    ThesiscommonsPreprints = provider_source_tag('thesiscommons', 'preprint')
    BodoarxivPreprints = provider_source_tag('bodoarxiv', 'preprint')
    OsfRegistries = provider_source_tag('osf', 'registry')
    Osf = provider_source_tag('osf')


# Needs to be updated when new providers are added.
class CampaignSourceTags(Enum):
    ErpChallenge = campaign_source_tag('erp_challenge')
    PreregChallenge = campaign_source_tag('prereg_challenge')
    Prereg = campaign_source_tag('prereg')
    OsfRegisteredReports = campaign_source_tag('osf_registered_reports')
    Osf4m = campaign_source_tag('osf4m')


# Needs to be updated when new providers are added.
class ProviderClaimedTags(Enum):
    AfricarxivPreprints = provider_claimed_tag('africarxiv', 'preprint')
    AgrixivPreprints = provider_claimed_tag('agrixiv', 'preprint')
    ArabixivPreprints = provider_claimed_tag('arabixiv', 'preprint')
    MetaarxivPreprints = provider_claimed_tag('metaarxiv', 'preprint')
    EartharxivPreprints = provider_claimed_tag('eartharxiv', 'preprint')
    EcoevorxivPreprints = provider_claimed_tag('ecoevorxiv', 'preprint')
    EcsarxivPreprints = provider_claimed_tag('ecsarxiv', 'preprint')
    EngrxivPreprints = provider_claimed_tag('engrxiv', 'preprint')
    FocusarchivePreprints = provider_claimed_tag('focusarchive', 'preprint')
    FrenxivPreprints = provider_claimed_tag('frenxiv', 'preprint')
    InarxivPreprints = provider_claimed_tag('inarxiv', 'preprint')
    LawarxivPreprints = provider_claimed_tag('lawarxiv', 'preprint')
    LissaPreprints = provider_claimed_tag('lissa', 'preprint')
    MarxivPreprints = provider_claimed_tag('marxiv', 'preprint')
    MediarxivPreprints = provider_claimed_tag('mediarxiv', 'preprint')
    MindrxivPreprints = provider_claimed_tag('mindrxiv', 'preprint')
    NutrixivPreprints = provider_claimed_tag('nutrixiv', 'preprint')
    OsfPreprints = provider_claimed_tag('osf', 'preprint')
    PaleorxivPreprints = provider_claimed_tag('paleorxiv', 'preprint')
    PsyarxivPreprints = provider_claimed_tag('psyarxiv', 'preprint')
    SocarxivPreprints = provider_claimed_tag('socarxiv', 'preprint')
    SportrxivPreprints = provider_claimed_tag('sportrxiv', 'preprint')
    ThesiscommonsPreprints = provider_claimed_tag('thesiscommons', 'preprint')
    BodoarxivPreprints = provider_claimed_tag('bodoarxiv', 'preprint')
    OsfRegistries = provider_claimed_tag('osf', 'registry')
    Osf = provider_claimed_tag('osf')


# Needs to be updated when new providers are added.
class CampaignClaimedTags(Enum):
    ErpChallenge = campaign_claimed_tag('erp_challenge')
    PreregChallenge = campaign_claimed_tag('prereg_challenge')
    Prereg = campaign_claimed_tag('prereg')
    OsfRegisteredReports = campaign_claimed_tag('osf_registered_reports')
    Osf4m = campaign_claimed_tag('osf4m')
