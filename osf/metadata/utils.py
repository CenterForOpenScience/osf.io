from website import settings


SUBJECT_SCHEME = 'bepress Digital Commons Three-Tiered Taxonomy'

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


def datacite_format_contributors(contributors):
    """ Format a list of contributors to match the datacite schema

    :param contributors_list: list of OSFUsers to format
    :return: formatted json for datacite
    """
    creators = []
    for contributor in contributors:
        name_identifiers = [
            {
                'nameIdentifier': contributor.absolute_url,
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

        creators.append({
            'creatorName': {
                'creatorName': contributor.fullname,
                'familyName': contributor.family_name,
                'givenName': contributor.given_name
            },
            'nameIdentifiers': name_identifiers
        })

    return creators


def datacite_format_subjects(subjects):
    return [
        {
            'subject': subject.bepress_subject.text if subject.bepress_subject else subject.text,
            'subjectScheme': SUBJECT_SCHEME
        }
        for subject in subjects
    ]


def datacite_format_identifier(target):
    identifier = target.get_identifier('doi')
    if identifier:
        return {
            'identifier': identifier.value,
            'identifierType': 'DOI'
        }


def datacite_format_rights(license):
    return {
        'rights': license.name,
        'rightsURI': license.url
    }
