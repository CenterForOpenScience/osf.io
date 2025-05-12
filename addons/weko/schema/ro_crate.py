import json
import logging
import re

from osf.models.metaschema import RegistrationSchema

from .base import (
    expand_listed_key, get_sources_for_key, find_schema_question, is_special_key, is_key_present, get_value, resolve_array_index
)


logger = logging.getLogger(__name__)


def _set_object_value(dest_object, key, value):
    logger.debug(f'SET {key} = {value}, target={dest_object}')
    key = key.lstrip('.')
    m = re.match(r'([^\.]+)\[([^]]+)\](\..+)?', key)
    if m:
        # Array
        key = m.group(1)
        index = m.group(2)
        subkey = m.group(3)
        if key not in dest_object:
            dest_object[key] = []
        else:
            if not isinstance(dest_object[key], list):
                raise ValueError(f'{key} is not an array')
        if not re.match(r'^[0-9]+$', index):
            raise ValueError(f'Invalid array index: {index}')
        index = int(index)
        current = len(dest_object[key])
        for i in range(current, index + 1):
            dest_object[key].append(None)
        if not subkey:
            dest_object[key][index] = value
            return
        if dest_object[key][index] is None:
            dest_object[key][index] = {}
        _set_object_value(dest_object[key][index], subkey.lstrip('.'), value)
        return
    m = re.match(r'([^\.]+)(\..+)?', key)
    if not m:
        raise ValueError(f'Invalid key: {key}')
    key = m.group(1)
    subkey = m.group(2)
    if not subkey:
        dest_object[key] = value
        return
    if key not in dest_object:
        dest_object[key] = {}
    else:
        if not isinstance(dest_object[key], dict):
            raise ValueError(f'{key} is not an object')
    _set_object_value(dest_object[key], subkey.lstrip('.'), value)

def _build_value(dest_object, full_key, value, weko_key_counts=None):
    if f'{full_key}.__value__' in weko_key_counts:
        if weko_key_counts[f'{full_key}.__value__'] != value:
            key_value = weko_key_counts[f'{full_key}.__value__']
            raise ValueError(f'Different values to the same key are detected: {value}, {key_value}')
        logger.debug(f'Skipped duplicated item: {full_key}')
        return []
    weko_key_counts[f'{full_key}.__value__'] = value
    _set_object_value(dest_object, full_key, value)

def _build_values(dest_object, file_metadata, weko_key_prefix, weko_props, weko_key_counts=None, commonvars=None, schema=None):
    if isinstance(weko_props, str):
        value = get_value(file_metadata, weko_props, commonvars=commonvars, schema=schema)
        _build_value(dest_object, weko_key_prefix, value, weko_key_counts=weko_key_counts)
        return
    for key in sorted(weko_props.keys()):
        items = weko_props[key]
        if key.startswith('@'):
            continue
        if not isinstance(items, list):
            items = [items]
        for item in items:
            if not is_key_present(file_metadata, item, commonvars=commonvars, schema=schema):
                continue
            full_key = resolve_array_index(weko_key_counts, f'{weko_key_prefix}.{key}')
            if isinstance(item, dict):
                # Subitem
                _build_values(
                    dest_object,
                    file_metadata,
                    full_key,
                    item,
                    weko_key_counts=weko_key_counts,
                    commonvars=commonvars,
                    schema=schema,
                )
                continue
            value = get_value(file_metadata, item, commonvars=commonvars, schema=schema)
            _build_value(dest_object, full_key, value, weko_key_counts=weko_key_counts)

def _flatten_json_ld_root(object):
    entities = []
    counts = {}
    for key, entity in object.items():
        if isinstance(entity, list):
            for e in entity:
                if '@id' not in e and '@type' not in e:
                    continue
                if '@id' not in e:
                    e['@id'] = _generate_json_ld_id(e, counts)
                entities += _flatten_json_ld(e, counts)
            continue
        if '@id' not in entity:
            continue
        entities += _flatten_json_ld(entity, counts)
    return sorted(entities, key=lambda x: x['@id'])

def _generate_json_ld_id(entity, counts):
    type_name = entity['@type']
    if isinstance(type_name, list):
        type_name = type_name[0]
    type_name = type_name.replace(':', '_')
    if type_name not in counts:
        counts[type_name] = 0
    counts[type_name] += 1
    return f'_:{type_name}{counts[type_name]}'

def _is_reference(value):
    if not isinstance(value, dict):
        return False
    keys = list(value.keys())
    return len(keys) == 1 and keys[0] == '@id'

def _is_literal(value):
    if isinstance(value, str):
        return True
    if isinstance(value, list):
        return all([isinstance(v, str) for v in value])

def _flatten_json_ld(object, counts):
    flattened_object = {}
    entities = [flattened_object]
    for key, value in object.items():
        if _is_literal(value) or _is_reference(value):
            flattened_object[key] = value
            continue
        if key in ['@id', '@type']:
            flattened_object[key] = value
            continue
        if isinstance(value, dict):
            if '@type' not in value:
                continue

            entity_id = value.get('@id', _generate_json_ld_id(value, counts))
            new_value = dict(value)
            new_value['@id'] = entity_id

            entities += _flatten_json_ld(new_value, counts)
            flattened_object[key] = {'@id': entity_id}
            continue
        if isinstance(value, list):
            new_value = []
            for v in value:
                if not isinstance(v, dict):
                    continue

                if _is_reference(v) or _is_literal(v):
                    new_value.append(v)
                    continue

                if '@type' not in v:
                    continue

                entity_id = v.get('@id', _generate_json_ld_id(v, counts))

                new_v = dict(v)
                new_v['@id'] = entity_id

                entities += _flatten_json_ld(new_v, counts)
                new_value.append({'@id': entity_id})

            flattened_object[key] = new_value
            continue
    return entities

def write_ro_crate_json(user, f, target_index, download_file_names, schema_id, file_metadatas, project_metadatas):
    from ..models import RegistrationMetadataMapping
    schema = RegistrationSchema.objects.get(_id=schema_id)
    mapping_def = RegistrationMetadataMapping.objects.filter(
        registration_schema_id=schema._id,
        filename='ro-crate-metadata.json',
    ).first()
    if mapping_def is None:
        raise ValueError(f'No mapping definition: {schema_id}')
    logger.debug(f'Mappings: {mapping_def.rules}')
    for i, file_metadata in enumerate(file_metadatas):
        logger.debug(f'File metadata #{i}: {file_metadata}')
    for i, project_metadata in enumerate(project_metadatas):
        logger.debug(f'Project metadata #{i}: {project_metadata}')

    mappings = expand_listed_key(mapping_def.rules)

    weko_key_counts = {}
    hierarchical_object = {}
    for key in sorted(mappings.keys()):
        for source, commonvars in get_sources_for_key(
            user, target_index, file_metadatas, download_file_names, project_metadatas, schema, key
        ):
            if key not in mappings:
                logger.warning(f'No mappings: {key}')
                continue
            weko_mapping = mappings[key]
            if weko_mapping is None:
                logger.debug(f'No mappings: {key}')
                continue
            source_data = source.get(key, {
                'value': '',
            }) if key != '_' else None
            question_schema = find_schema_question(schema.schema, key) if not is_special_key(key) else None
            if key == '_' or weko_mapping.get('@type', None) == 'string':
                if not is_key_present(
                    source_data,
                    weko_mapping,
                    commonvars=commonvars,
                    schema=question_schema,
                ):
                    logger.debug(f'Skipped: {key}')
                    continue
                _build_values(
                    hierarchical_object,
                    source_data,
                    '',
                    weko_mapping,
                    weko_key_counts=weko_key_counts,
                    commonvars=commonvars,
                    schema=question_schema,
                )
                continue
            if weko_mapping['@type'] in ['array', 'jsonarray']:
                value = source_data.get('value', '')
                if weko_mapping['@type'] == 'jsonarray':
                    if value is None or not isinstance(value, str):
                        logger.warn(f'Unexpected value: {value}, {key}')
                        continue
                    jsonarray = json.loads(value) if value is not None and len(value) > 0 else []
                else:
                    if value is None or not isinstance(value, list):
                        logger.warn(f'Unexpected value: {value}, {key}')
                        continue
                    jsonarray = value if value is not None else []
                for i, jsonelement in enumerate(jsonarray):
                    target_data = {
                        'object': jsonelement,
                    }
                    if not is_key_present(
                        target_data,
                        weko_mapping,
                        commonvars=commonvars,
                        schema=question_schema,
                    ):
                        logger.debug(f'Skipped: {key}[{i}]')
                        continue
                    _build_values(
                        hierarchical_object,
                        target_data,
                        '',
                        weko_mapping,
                        weko_key_counts=weko_key_counts,
                        commonvars=commonvars,
                        schema=question_schema,
                    )
                continue
            if weko_mapping['@type'] in ['object', 'jsonobject']:
                value = source_data.get('value', '')
                if weko_mapping['@type'] == 'jsonobject':
                    if value is None or not isinstance(value, str):
                        logger.warn(f'Unexpected value: {value}, {key}')
                        continue
                    jsonobject = json.loads(value) if value is not None and len(value) > 0 else {}
                else:
                    if value is None or not isinstance(value, dict):
                        logger.warn(f'Unexpected value: {value}, {key}')
                        continue
                    jsonobject = value if value is not None else {}
                target_data = {
                    'object': jsonobject,
                }
                if not is_key_present(
                    target_data,
                    weko_mapping,
                    commonvars=commonvars,
                    schema=question_schema,
                ):
                    logger.debug(f'Skipped: {key}')
                    continue
                _build_values(
                    hierarchical_object,
                    target_data,
                    '',
                    weko_mapping,
                    weko_key_counts=weko_key_counts,
                    commonvars=commonvars,
                    schema=question_schema,
                )
                continue
            type_value = weko_mapping['@type']
            raise ValueError(f'Unexpected type: {type_value}')
    json_ld = {
        '@context': [
            'https://w3id.org/ro/crate/1.1/context',
            'http://purl.org/wk/v1/wk-context.jsonld',
            {
                'ams:analysisType': 'https://purl.org/rdm/ontology/analysisType',
                'ams:descriptionOfExperimentalCondition': 'https://purl.org/rdm/ontology/descriptionOfExperimentalCondition',
                'ams:purposeOfExperiment': 'https://purl.org/rdm/ontology/purposeOfExperiment',
                'rdm:name': 'https://purl.org/rdm/ontology/name',
                'dc:type': 'http://purl.org/dc/elements/1.1/type'
            },
            {
                'ams': 'https://purl.org/rdm/ontology/'
            },
            {
                'wk': 'https://purl.org/rdm/ontology/'
            },
            {
                'rdm': 'https://purl.org/rdm/ontology/'
            },
            {
                'odrl': 'http://www.w3.org/ns/odrl.jsonld'
            },
            {
                'dc': 'http://purl.org/dc/elements/1.1/'
            },
            {
                'jpcoar': 'https://github.com/JPCOAR/schema/blob/master/2.0/'
            },
            {
                'datacite': 'http://datacite.org/schema/kernel-4'
            }
        ],
        '@graph': _flatten_json_ld_root(hierarchical_object),
    }
    json.dump(json_ld, f, indent=2, ensure_ascii=False)
