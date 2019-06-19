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
        ProviderSourceTags.OsfRegistries.value
    ]
    for i in user.system_tags:
        if i in entry_points:
            return i
    else:
        return 'osf'


def provider_source_tag(service, provider_id):
    if service:
        return 'source:provider|{}|{}'.format(service, provider_id)
    else:
        return 'source:provider|{}'.format(provider_id)


def campaign_source_tag(campaign_name):
    return 'source:campaign|{}'.format(campaign_name)


def provider_claimed_tag(service, provider_id):
    if service:
        return 'claimed:provider|{}|{}'.format(service, provider_id)
    else:
        return 'claimed:provider|{}'.format(provider_id)


def campaign_claimed_tag(campaign_name):
    return 'claimed:campaign|{}'.format(campaign_name)


class ProviderSourceTags(Enum):
    AfricaxvPreprints = provider_source_tag('preprint', 'africarxiv')
    AgrixivPreprints = provider_source_tag('preprint', 'agrixiv')
    ArabixivPreprints = provider_source_tag('preprint', 'arabixiv')
    MetaarxivPreprints = provider_source_tag('preprint', 'metaarxiv')
    EartharxivPreprints = provider_source_tag('preprint', 'eartharxiv')
    EcoevorxivPreprints = provider_source_tag('preprint', 'ecoevorxiv')
    EcsarxivPreprints = provider_source_tag('preprint', 'ecsarxiv')
    EngrxivPreprints = provider_source_tag('preprint', 'engrxiv')
    FocusarchivePreprints = provider_source_tag('preprint', 'focusarchive')
    FrenxivPreprints = provider_source_tag('preprint', 'frenxiv')
    InarxivPreprints = provider_source_tag('preprint', 'inarxiv')
    LawarxivPreprints = provider_source_tag('preprint', 'lawarxiv')
    LissaPreprints = provider_source_tag('preprint', 'lissa')
    MarxivPreprints = provider_source_tag('preprint', 'marxiv')
    MediarxivPreprints = provider_source_tag('preprint', 'mediarxiv')
    MindrxivPreprints = provider_source_tag('preprint', 'mindrxiv')
    NutrixivPreprints = provider_source_tag('preprint', 'nutrixiv')
    OsfPreprints = provider_source_tag('preprint', 'osf')
    PaleorxivPreprints = provider_source_tag('preprint', 'paleorxiv')
    PsyarxivPreprints = provider_source_tag('preprint', 'psyarxiv')
    SocarxivPreprints = provider_source_tag('preprint', 'socarxiv')
    SportrxivPreprints = provider_source_tag('preprint', 'sportrxiv')
    ThesiscommonsPreprints = provider_source_tag('preprint', 'thesiscommons')
    BodoarxivPreprints = provider_source_tag('preprint', 'bodoarxiv')
    OsfRegistries = provider_source_tag('registry', 'osf')
    Osf = provider_source_tag(None, 'osf')


class CampaignSourceTags(Enum):
    ErpChallenge = campaign_source_tag('erp_challenge')
    PreregChallenge = campaign_source_tag('prereg_challenge')
    Prereg = campaign_source_tag('prereg')
    OsfRegisteredReports = campaign_source_tag('osf_registered_reports')
    Osf4m = campaign_source_tag('osf4m')


class ProviderClaimedTags(Enum):
    AfricaxvPreprints = provider_claimed_tag('preprint', 'africarxiv')
    AgrixivPreprints = provider_claimed_tag('preprint', 'agrixiv')
    ArabixivPreprints = provider_claimed_tag('preprint', 'arabixiv')
    MetaarxivPreprints = provider_claimed_tag('preprint', 'metaarxiv')
    EartharxivPreprints = provider_claimed_tag('preprint', 'eartharxiv')
    EcoevorxivPreprints = provider_claimed_tag('preprint', 'ecoevorxiv')
    EcsarxivPreprints = provider_claimed_tag('preprint', 'ecsarxiv')
    EngrxivPreprints = provider_claimed_tag('preprint', 'engrxiv')
    FocusarchivePreprints = provider_claimed_tag('preprint', 'focusarchive')
    FrenxivPreprints = provider_claimed_tag('preprint', 'frenxiv')
    InarxivPreprints = provider_claimed_tag('preprint', 'inarxiv')
    LawarxivPreprints = provider_claimed_tag('preprint', 'lawarxiv')
    LissaPreprints = provider_claimed_tag('preprint', 'lissa')
    MarxivPreprints = provider_claimed_tag('preprint', 'marxiv')
    MediarxivPreprints = provider_claimed_tag('preprint', 'mediarxiv')
    MindrxivPreprints = provider_claimed_tag('preprint', 'mindrxiv')
    NutrixivPreprints = provider_claimed_tag('preprint', 'nutrixiv')
    OsfPreprints = provider_claimed_tag('preprint', 'osf')
    PaleorxivPreprints = provider_claimed_tag('preprint', 'paleorxiv')
    PsyarxivPreprints = provider_claimed_tag('preprint', 'psyarxiv')
    SocarxivPreprints = provider_claimed_tag('preprint', 'socarxiv')
    SportrxivPreprints = provider_claimed_tag('preprint', 'sportrxiv')
    ThesiscommonsPreprints = provider_claimed_tag('preprint', 'thesiscommons')
    BodoarxivPreprints = provider_claimed_tag('preprint', 'bodoarxiv')
    OsfRegistries = provider_claimed_tag('registry', 'osf')
    Osf = provider_claimed_tag(None, 'osf')


class CampaignClaimedTags(Enum):
    ErpChallenge = campaign_claimed_tag('erp_challenge')
    PreregChallenge = campaign_claimed_tag('prereg_challenge')
    Prereg = campaign_claimed_tag('prereg')
    OsfRegisteredReports = campaign_claimed_tag('osf_registered_reports')
    Osf4m = campaign_claimed_tag('osf4m')
