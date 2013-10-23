COMMENT_SCHEMA = {
    'schema': [
        {
            'id': 'comment',
            'type': 'textarea',
            'label': 'What do you think?',

        },
        {
            'id': 'rating',
            'type': 'select',
            'options': ['bad', 'ok', 'good'],
            'caption': 'choose rating',
            'label': 'choose rating',
        },
    ],
    'category': 'comment',
    'version': '1',
}

OPEN_REGISTRATION_SCHEMA = {
    'schema': [
        {
            'id': 'summary',
            'type': 'textarea',
            'label': 'Provide a narrative summary of what is contained in this '
                    'registration, or how it differs from prior registrations.',
        },
    ],
    'category': 'registration',
    'version': '1',
}

STANDARD_REGISTRATION_SCHEMA = {
    'schema': [
        {
            'id': 'datacompletion',
            'type': 'select',
            'label': 'Is data collection for this project underway or complete?',
            'caption': 'Please choose',
            'options': ['No', 'Yes'],
        },
        {
            'id': 'looked',
            'type': 'select',
            'label': 'Have you looked at the data?',
            'caption': 'Please choose',
            'options': ['No', 'Yes'],
        },
        {
            'id': 'comments',
            'type': 'textarea',
            'label': 'Other Comments',
        },
    ],
    'category': 'registration',
    'version': '1',
}

# Collect schemas

OSF_META_SCHEMAS = {
    'osf_comment': COMMENT_SCHEMA,
    'Open-Ended_Registration': OPEN_REGISTRATION_SCHEMA,
    'OSF-Standard_Pre-Data_Collection_Registration': STANDARD_REGISTRATION_SCHEMA,
}
