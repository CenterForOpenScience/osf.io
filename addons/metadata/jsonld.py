import json
import logging

from osf.models.metaschema import RegistrationSchema


logger = logging.getLogger(__name__)


def _get_registration_schema_as_json_ld_entity(registration_schema, schema_ids):
    registration_schema_id = f'#metadata-schema-{registration_schema.name}-{registration_schema.schema_version}'
    if registration_schema_id not in schema_ids:
        schema_props = {
            '@type': 'RDMMetadataSchema',
            'name': registration_schema.name,
            'version': registration_schema.schema_version,
        }
        schema_ids[registration_schema_id] = schema_props
    return registration_schema_id

def _convert_file_metadata_item_to_json_ld_entity(item, schema_ids):
    schema = item['schema']
    r = {
        '@type': 'RDMFileMetadata',
        'version': 'active' if item.get('active', False) else '',
        'encodingFormat': 'application/json',
        'text': json.dumps(item['data']),
    }
    try:
        registration_schema = RegistrationSchema.objects.get(_id=schema)
        registration_schema_id = _get_registration_schema_as_json_ld_entity(registration_schema, schema_ids)
        r.update({
            'rdmSchema': {
                '@id': registration_schema_id,
            }
        })
    except RegistrationSchema.DoesNotExist:
        logger.warn(f'Registration schema is not found: {schema}')
    return r

def convert_project_metadata_to_json_ld_entities(draft_or_registration):
    schema_ids = {}
    schema = draft_or_registration.registration_schema
    metadata = {
        '@type': 'RDMProjectMetadata',
        'encodingFormat': 'application/json',
        'rdmSchema': {
            '@id': _get_registration_schema_as_json_ld_entity(schema, schema_ids),
        },
        'text': json.dumps(draft_or_registration.get_registration_metadata(schema)),
        'dateCreated': draft_or_registration.created.isoformat(),
        'dateModified': draft_or_registration.modified.isoformat(),
    }
    return metadata, schema_ids

def convert_file_metadata_to_json_ld_entities(metadata):
    schema_ids = {}
    metadatas = [
        _convert_file_metadata_item_to_json_ld_entity(item, schema_ids)
        for item in metadata['items']
    ]
    return metadatas, schema_ids

def convert_json_ld_entity_to_file_metadata_item(props, crate):
    if props['@type'] != 'RDMFileMetadata':
        raise ValueError(f'Unexpected type: {props["@type"]}')
    if 'rdmSchema' not in props:
        return None
    schema_entity = crate.get(props['rdmSchema']['@id'])
    registration_schema = RegistrationSchema.objects.filter(
        name=schema_entity.properties()['name'],
    ).order_by('-schema_version').first()
    if registration_schema is None:
        return None
    return {
        'active': props.get('version', '') == 'active',
        'schema': registration_schema._id,
        'data': json.loads(props['text']),
    }
