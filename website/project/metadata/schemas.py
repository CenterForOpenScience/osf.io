import os
import json

def _id_to_name(id):
    return ' '.join(id.split('_'))

def _name_to_id(name):
    return '_'.join(name.split(' '))

def ensure_schema_structure(schema):
    schema['pages'] = schema.get('pages', [])
    schema['title'] = schema['name']
    schema['version'] = schema.get('version', 1)
    return schema

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)

OSF_META_SCHEMAS = [
    ensure_schema_structure(from_json('osf-open-ended-1.json')),
    ensure_schema_structure(from_json('osf-open-ended-2.json')),
    ensure_schema_structure(from_json('osf-standard-1.json')),
    ensure_schema_structure(from_json('osf-standard-2.json')),
    ensure_schema_structure(from_json('brandt-prereg-1.json')),
    ensure_schema_structure(from_json('brandt-prereg-2.json')),
    ensure_schema_structure(from_json('brandt-postcomp-1.json')),
    ensure_schema_structure(from_json('brandt-postcomp-2.json')),
    ensure_schema_structure(from_json('prereg-prize.json')),
    ensure_schema_structure(from_json('confirmatory-general-2.json')),
    ensure_schema_structure(from_json('egap-project-2.json')),
]

ACTIVE_META_SCHEMAS = (
    'Open-Ended Registration',
    'OSF-Standard Pre-Data Collection Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    'Replication Recipe (Brandt et al., 2013): Post-Completion',
    'Prereg Challenge',
)
