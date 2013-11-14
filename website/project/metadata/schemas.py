import os
import json

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

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname):
    return json.load(open(os.path.join(here, fname)))

OSF_META_SCHEMAS = {
    #'osf_comment': ensure_schema_structure(COMMENT_SCHEMA),
    'Open-Ended_Registration': ensure_schema_structure(from_json('osf-open-ended.json')),
    'OSF-Standard_Pre-Data_Collection_Registration': ensure_schema_structure(from_json('osf-standard.json')),
    'Brandt_Preregistration': ensure_schema_structure(from_json('brandt-prereg.json')),
    'AEA_Preregistration': ensure_schema_structure(from_json('aea-prereg.json')),
}
