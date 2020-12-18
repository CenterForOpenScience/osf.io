from website import settings


BEPRESS_SUBJECT_SCHEME = 'bepress Digital Commons Three-Tiered Taxonomy'

DATACITE_RESOURCE_TYPE_MAP = {
    'Audio/Video': 'Audiovisual',
    'Dataset': 'Dataset',
    'Image': 'Image',
    'Model': 'Model',
    'Software': 'Software',
    'Book': 'Text',
    'Funding Submission': 'Text',
    'Journal Article': 'Text',
    'Lesson': 'Text',
    'Poster': 'Text',
    'Preprint': 'Text',
    'Presentation': 'Text',
    'Research Tool': 'Text',
    'Thesis': 'Text',
    'Other': 'Text',
    '(:unas)': 'Other'
}


def datacite_format_creators(creators):
    """ Format a list of contributors to match the datacite schema
    Schema found here: https://schema.datacite.org/meta/kernel-4.3/doc/DataCite-MetadataKernel_v4.3.pdf

    :param contributors_list: list of OSFUsers to format
    :return: formatted json for datacite
    """
    creators_json = []
    for creator in creators:
        name_identifiers = [
            {
                'nameIdentifier': f'{creator._id}/',
                'nameIdentifierScheme': 'OSF',
                'schemeURI': settings.DOMAIN
            }
        ]

        if creator.external_identity.get('ORCID'):
            verified = list(creator.external_identity['ORCID'].values())[0] == 'VERIFIED'
            if verified:
                name_identifiers.append({
                    'nameIdentifier': list(creator.external_identity['ORCID'].keys())[0],
                    'nameIdentifierScheme': 'ORCID',
                    'schemeURI': 'http://orcid.org/'
                })

        creators_json.append({
            'nameIdentifiers': name_identifiers,
            'creatorName': creator.fullname,
            'familyName': creator.family_name,
            'givenName': creator.given_name
        })

    return creators_json


def datacite_format_contributors(contributors):
    """ Format a list of contributors to match the datacite schema
    Schema found here: https://schema.datacite.org/meta/kernel-4.3/doc/DataCite-MetadataKernel_v4.3.pdf

    :param contributors_list: list of OSFUsers to format
    :return: formatted json for datacite
    """
    contributors_json = []
    for contributor in contributors:
        name_identifiers = [
            {
                'nameIdentifier': f'{contributor._id}/',
                'nameIdentifierScheme': 'OSF',
                'schemeURI': settings.DOMAIN
            }
        ]

        if contributor.external_identity.get('ORCID'):
            verified = list(contributor.external_identity['ORCID'].values())[0] == 'VERIFIED'
            if verified:
                name_identifiers.append({
                    'nameIdentifier': list(contributor.external_identity['ORCID'].keys())[0],
                    'nameIdentifierScheme': 'ORCID',
                    'schemeURI': 'http://orcid.org/'
                })

        contributors_json.append({
            'nameIdentifiers': name_identifiers,
            'contributorName': contributor.fullname,
            'contributorType': 'ProjectMember',
            'familyName': contributor.family_name,
            'givenName': contributor.given_name
        })

    return contributors_json


def datacite_format_subjects(node):
    """ Format a list of subjects to match the datacite schema
    Schema found here: https://schema.datacite.org/meta/kernel-4.3/doc/DataCite-MetadataKernel_v4.3.pdf

    :param node: a project or registration that should have it's subject formatted for datacite
    :return: formatted json for datacite
    """
    datacite_subjects = []
    subjects = node.subjects.all().select_related('bepress_subject')
    if subjects.exists():
        datacite_subjects = [
            {
                'subject': subject.bepress_subject.text if subject.bepress_subject else subject.text,
                'subjectScheme': BEPRESS_SUBJECT_SCHEME
            }
            for subject in subjects
        ]
    tags = node.tags.filter(system=False)
    datacite_subjects += [
        {'subject': tag.name,
         'subjectScheme': 'OSF tag'
         } for tag in tags
    ]
    return datacite_subjects


def datacite_format_rights(license):
    """ Format the liceses/rights of project/node for a datacite schema
    Schema found here: https://schema.datacite.org/meta/kernel-4.3/doc/DataCite-MetadataKernel_v4.3.pdf

    :param license: a lincense object for a node that should be formatted for datacite
    :return: formatted json for datacite
    """

    return {
        'rights': license.name,
        'rightsURI': license.url
    }
