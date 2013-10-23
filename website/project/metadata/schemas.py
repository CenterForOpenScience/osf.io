COMMENT_SCHEMA = {
    'schema': {
        'questions': [
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
    },
    'category': 'comment',
    'version': '1',
}

OPEN_REGISTRATION_SCHEMA = {
    'schema': {
        'questions': [
            {
                'id': 'summary',
                'type': 'textarea',
                'label': 'Provide a narrative summary of what is contained in this '
                        'registration, or how it differs from prior registrations.',
            },
        ],
    },
    'category': 'registration',
    'version': '1',
}

STANDARD_REGISTRATION_SCHEMA = {
    'schema': {
        'questions': [
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
    },
    'category': 'registration',
    'version': '1',
}

BRANDT_PREREGISTRATION = {
    'schema': {
        'pages': [
            {
                'id': 'page1',
                'title': 'The Nature of the Effect',
                'questions': [
                    {'type': 'textarea',  'id': 'item1', 'label': 'Verbal description of the effect I am trying to replicate'},
                    {'type': 'textarea',  'id': 'item2', 'label': 'It is important to replicate this effect because'},
                    {'type': 'textfield', 'id': 'item3', 'label': 'The effect size of the effect I am trying to replicate is'},
                    {'type': 'textfield', 'id': 'item4', 'label': 'The confidence interval of the original effect is'},
                    {'type': 'textfield', 'id': 'item5', 'label': 'The sample size of the original effect is'},
                    {'type': 'textfield', 'id': 'item6', 'label': 'Where was the original study conducted? (e.g., lab, in the field, online)'},
                    {'type': 'textfield', 'id': 'item7', 'label': 'What country/region was the original study conducted in?'},
                    {'type': 'textfield', 'id': 'item8', 'label': 'What kind of sample did the original study use? (e.g., student, Mturk, representative)'},
                    {'type': 'textfield', 'id': 'item9', 'label': 'Was the original study conducted with paper-and-pencil surveys, on a computer, or something else?'},
                ],
            },
            {
                'id': 'page2',
                'title': 'Designing the Replication Study',
                'questions': [
                    {'type': 'select',    'id': 'item10', 'label': 'Are the original materials for the study available from the author?', 'options': ['yes', 'no'], 'caption': 'Choose...'},
                    {'type': 'textarea',  'id': 'item11', 'label': 'I know that assumptions (e.g., about the meaning of the stimuli) in the original study will also hold in my replication because'},
                    {'type': 'textfield', 'id': 'item12', 'label': 'Location of the experimenter during data collection'},
                    {'type': 'textfield', 'id': 'item13', 'label': 'Experimenter knowledge of participant experimental condition'},
                    {'type': 'textfield', 'id': 'item14', 'label': 'Experimenter knowledge of overall hypotheses'},
                    {'type': 'textfield', 'id': 'item15', 'label': 'My target sample size is'},
                    {'type': 'textarea',  'id': 'item16', 'label': 'The rationale for my sample size is'},
                ],
            },
            {
                'id': 'page3',
                'title': 'Documenting Differences between the Original and Replication Study',
                'questions': [
                    {'type': 'select',   'id': 'item17', 'label': 'The similarities/differences in the instructions are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'select',   'id': 'item18', 'label': 'The similarities/differences in the measures are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'select',   'id': 'item19', 'label': 'The similarities/differences in the stimuli are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'select',   'id': 'item20', 'label': 'The similarities/differences in the procedure are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'select',   'id': 'item21', 'label': 'The similarities/differences in the location (e.g., lab vs. online; alone vs. in groups) are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'select',   'id': 'item22', 'label': 'The similarities/difference in remuneration are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'select',   'id': 'item23', 'label': 'The similarities/differences between participant populations are', 'options': ['Exact', 'Close', 'Different'], 'caption': 'Choose...'},
                    {'type': 'textarea', 'id': 'item24', 'label': 'What differences between the original study and your study might be expected to influence the size and/or direction of the effect?'},
                    {'type': 'textarea', 'id': 'item25', 'label': 'I have taken the following steps to test whether the differences listed in #22 will influence the outcome of my replication attempt'},
                ],
            },
            {
                'id': 'page4',
                'title': 'Analysis and Replication Evaluation',
                'questions': [
                    {'type': 'textarea', 'id': 'item26', 'label': 'My exclusion criteria are (e.g., handling outliers, removing participants from analysis)'},
                    {'type': 'textarea', 'id': 'item27', 'label': 'My analysis plan is (justify differences from the original)'},
                    {'type': 'textarea', 'id': 'item28', 'label': 'A successful replication is defined as'},
                ],
            },
            {
                'id': 'page5',
                'title': 'Registering the Replication Attempt',
                'questions': [
                    {'type': 'textfield', 'id': 'item29', 'label': 'The finalized materials, procedures, analysis plan etc of the replication are registered here'},
                ],
            },
            {
                'id': 'page6',
                'title': 'Reporting the Replication',
                'questions': [
                    {'type': 'textfield', 'id': 'item30', 'label': 'The effect size of the replication is'},
                    {'type': 'textfield', 'id': 'item31', 'label': 'The confidence interval of the replication effect size is'},
                    {'type': 'select',    'id': 'item32', 'label': 'The replication effect size is', 'options': ['significantly different from the original effect size', 'not significantly different from the original effect size'], 'caption': 'Choose...'},
                    {'type': 'select',    'id': 'item33', 'label': 'I judge the replication to be a(n)', 'options': ['success', 'informative failure to replicate', 'practical failure to replicate', 'inconclusive'], 'caption': 'Choose...'},
                    {'type': 'textarea',  'id': 'item34', 'label': 'I judge it so because'},
                    {'type': 'textfield', 'id': 'item35', 'label': 'Interested experts can obtain my data and syntax here'},
                    {'type': 'textfield', 'id': 'item36', 'label': 'All of the analyses were reported in the report or are available here'},
                    {'type': 'textarea',  'id': 'item37', 'label': 'The limitations of my replication study are'},
                ],
            },
        ],
    },
    'category': 'registration',
    'version': '1',
}

# Collect schemas

def ensure_schema_structure(schema):
    if 'pages' not in schema['schema']:
        schema['schema'] = {
            'pages': [
                {
                    'id': 'page1',
                    'title': '',
                    'questions': schema['schema']['questions'],
                }
            ]
        }
    return schema

OSF_META_SCHEMAS = {
    'osf_comment': ensure_schema_structure(COMMENT_SCHEMA),
    'Open-Ended_Registration': ensure_schema_structure(OPEN_REGISTRATION_SCHEMA),
    'OSF-Standard_Pre-Data_Collection_Registration': ensure_schema_structure(STANDARD_REGISTRATION_SCHEMA),
    'brandt_preregistration': ensure_schema_structure(BRANDT_PREREGISTRATION),
}
