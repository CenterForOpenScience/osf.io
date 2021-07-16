import os
import json

# Relative path-names of json text files containing standard schemas
OSF_META_SCHEMA_FILES = [
    'osf-open-ended-2.json',
    'osf-open-ended-3.json',
    'osf-standard-2.json',
    'brandt-prereg-2.json',
    'brandt-postcomp-2.json',
    'character-lab-fully-powered-study.json',
    'character-lab-pilot-study.json',
    'prereg-prize.json',
    'erpc-prize.json',
    'confirmatory-general-2.json',
    'egap-project-2.json',
    'veer-1.json',
    'aspredicted.json',
    'registered-report.json',
    'registered-report-3.json',
    'registered-report-4.json',
    'ridie-initiation.json',
    'ridie-complete.json',
    'osf-preregistration.json',
    'osf-preregistration-3.json',
    'egap-registration.json',
    'egap-registration-3.json',
    'egap-registration-4.json',
    'egap-legacy-registration.json',
    'asist-hypothesis-capability-registration.json',
    'asist-results-registration.json',
    'real-world-evidence.json',
    'qualitative-research.json',
    'secondary-data.json',
    'hypothesis-testing-studies-using-youth-data.json',
    'other-studies-using-youth-data.json'
]

METASCHEMA_ORDERING = (
    'OSF Preregistration',
    'Open-Ended Registration',
    'Preregistration Template from AsPredicted.org',
    'Registered Report Protocol Preregistration',
    'OSF-Standard Pre-Data Collection Registration',
    'OSF-Secondary Data Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    'Replication Recipe (Brandt et al., 2013): Post-Completion',
    "Pre-Registration in Social Psychology (van 't Veer & Giner-Sorolla, 2016): Pre-Registration",
    'Election Research Preacceptance Competition',
    'RIDIE Registration - Study Initiation',
    'RIDIE Registration - Study Complete',
    'EGAP Registration',
    'Qualitative Preregistration',
    'Real World Evidence in Health Outcomes Minimum Recommended Form',
    'Qualitative Preregistration',
    'ASIST Results Registration',
    'ASIST Hypothesis/Capability Registration',
)


here = os.path.split(os.path.abspath(__file__))[0]

def _id_to_name(id):
    return ' '.join(id.split('_'))

def _name_to_id(name):
    return '_'.join(name.split(' '))

def ensure_schema_structure(schema):
    schema['pages'] = schema.get('pages', [])
    schema['title'] = schema['name']
    schema['version'] = schema.get('version', 1)
    return schema


def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)

def get_osf_meta_schemas():
    """Returns the current contents of all known schema files."""
    schemas = [
        ensure_schema_structure(from_json(json_filename))
        for json_filename in OSF_META_SCHEMA_FILES
    ]
    return schemas
