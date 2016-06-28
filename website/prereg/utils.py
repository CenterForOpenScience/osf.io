from modularodm import Q

PREREG_CAMPAIGNS = {
    'prereg': 'Prereg Challenge',
    'erpc': 'Election Research Preacceptance Challenge',
}

PREREG_LANGUAGE = {
    'prereg': {
        'description': 'The process of preregistering your plans is beneficial to both the scientific field and to you, the scientist. By writing out detailed data collection methods, analysis plans, and rules for excluding or missing data, you can make important decisions that affect your workflow earlier, without the biases that occur once the data are in front of you.',
        'steps': ['Specify all your study and analysis decisions prior to investigating your data', 'Publish your study in an eligible journal', 'Receive $1,000'],
        'kind': 'preregistration',
        'info_url': 'http://www.cos.io/prereg',
    },
    'erpc': {
        'description': 'The process of creating a preregistered analysis plan is beneficial to both the scientific field and to you, the scientist. By writing out detailed analysis plans before examining into the data, you can make important decisions that affect your workflow earlier, without the biases that occur once the data are in front of you.',
        'steps': ['Specify all analysis decisions prior to investigating your data', 'Publish your study in an eligible journal', 'Receive $2,000'],
        'kind': 'preregistered analysis plan',
        'info_url': 'http://www.erpc.org',
    }
}

def get_prereg_schema(campaign='prepreg'):
    from website.models import MetaSchema  # noqa
    schame_name = PREREG_CAMPAIGNS.get(campaign) or PREREG_CAMPAIGNS.get('prereg')

    return MetaSchema.find_one(
        Q('name', 'eq', schame_name) &
        Q('schema_version', 'eq', 2)
    )

def serialize_campaign_context(campaign):
    ret = {
        'campaign_long': PREREG_CAMPAIGNS[campaign],
        'campaign_short': campaign
    }
    ret.update(PREREG_LANGUAGE[campaign])
    return ret
