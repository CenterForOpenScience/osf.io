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
    ensure_schema_structure(from_json('osf-open-ended-2.json')),
    ensure_schema_structure(from_json('osf-open-ended-3.json')),
    ensure_schema_structure(from_json('osf-standard-2.json')),
    ensure_schema_structure(from_json('brandt-prereg-2.json')),
    ensure_schema_structure(from_json('brandt-postcomp-2.json')),
    ensure_schema_structure(from_json('prereg-prize.json')),
    ensure_schema_structure(from_json('erpc-prize.json')),
    ensure_schema_structure(from_json('confirmatory-general-2.json')),
    ensure_schema_structure(from_json('egap-project-2.json')),
    ensure_schema_structure(from_json('veer-1.json')),
    ensure_schema_structure(from_json('aspredicted.json')),
    ensure_schema_structure(from_json('registered-report.json')),
    ensure_schema_structure(from_json('registered-report-3.json')),
    ensure_schema_structure(from_json('registered-report-4.json')),
    ensure_schema_structure(from_json('ridie-initiation.json')),
    ensure_schema_structure(from_json('ridie-complete.json')),
    ensure_schema_structure(from_json('osf-preregistration.json')),
    ensure_schema_structure(from_json('osf-preregistration-3.json')),
    ensure_schema_structure(from_json('egap-registration.json')),
    ensure_schema_structure(from_json('egap-registration-3.json')),
    ensure_schema_structure(from_json('e-rad-metadata-1.json')),
    ensure_schema_structure(from_json('ms2-mibyodb-metadata.json')),
]

METASCHEMA_ORDERING = (
    'Prereg Challenge',
    'OSF Preregistration',
    'Open-Ended Registration',
    'Preregistration Template from AsPredicted.org',
    'Registered Report Protocol Preregistration',
    'OSF-Standard Pre-Data Collection Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    'Replication Recipe (Brandt et al., 2013): Post-Completion',
    "Pre-Registration in Social Psychology (van 't Veer & Giner-Sorolla, 2016): Pre-Registration",
    'Election Research Preacceptance Competition',
    'RIDIE Registration - Study Initiation',
    'RIDIE Registration - Study Complete',
    'EGAP Registration',
    '公的資金による研究データのメタデータ登録',
    'ムーンショット目標2データベース（未病DB）のメタデータ登録',
)
