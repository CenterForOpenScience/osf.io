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


def datacite_format_name_identifiers(user):
    data = {
        'nameIdentifiers': [
            {
                'nameIdentifier': f'{settings.DOMAIN}{user._id}/',
                'nameIdentifierScheme': 'URL',
            }
        ]
    }
    orcid = user.get_verified_external_id('ORCID', verified_only=True)
    if orcid:
        data['nameIdentifiers'].append({
            'nameIdentifier': orcid,
            'nameIdentifierScheme': 'ORCID',
            'schemeURI': 'http://orcid.org/'
        })

    return data


def datacite_format_affiliations(user):
    data = {'affiliation': []}
    for affiliated_institution in user.affiliated_institutions.all():
        data['affiliation'].append({
            'name': affiliated_institution.name,
        })

        if affiliated_institution.identifier_domain:
            data['affiliation'].append({
                'name': affiliated_institution.name,
                'affiliationIdentifier': affiliated_institution.identifier_domain,
                'affiliationIdentifierScheme': 'URL',
            })

        if affiliated_institution.ror_uri:
            data['affiliation'].append(
                {
                    'name': affiliated_institution.name,
                    'affiliationIdentifier': affiliated_institution.ror_uri,
                    'affiliationIdentifierScheme': 'ROR',
                    'SchemeURI': 'https://ror.org/',
                }
            )

    return data


def datacite_format_creators(creators):
    """ Format a list of contributors to match the datacite schema
    Schema found here: https://schema.datacite.org/meta/kernel-4.3/doc/DataCite-MetadataKernel_v4.3.pdf

    :param creators: list of OSFUsers to format
    :return: formatted json for datacite
    """
    creators_json = []
    for creator in creators:
        data = {}
        if creator.affiliated_institutions.exists():
            data.update(datacite_format_affiliations(creator))
        data.update(datacite_format_name_identifiers(creator))
        data.update({
            'nameType': 'Personal',
            'creatorName': creator.fullname,
            'familyName': creator.family_name,
            'givenName': creator.given_name,
            'name': creator.fullname
        })
        creators_json.append(data)

    return creators_json


def datacite_format_contributors(contributors):
    """ Format a list of contributors to match the datacite schema
    Schema found here: https://schema.datacite.org/meta/kernel-4.3/doc/DataCite-MetadataKernel_v4.3.pdf

    :param contributors: list of OSFUsers to format
    :return: formatted json for datacite
    """
    contributors_json = []
    for contributor in contributors:
        data = {}
        if contributor.affiliated_institutions.exists():
            data.update(datacite_format_affiliations(contributor))
        data.update(datacite_format_name_identifiers(contributor))
        data.update({
            'nameType': 'Personal',
            'contributorType': 'ProjectMember',
            'contributorName': contributor.fullname,
            'familyName': contributor.family_name,
            'givenName': contributor.given_name,
            'name': contributor.fullname,
        })
        contributors_json.append(data)
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
