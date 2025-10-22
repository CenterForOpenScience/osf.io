import csv
import json
import logging

from osf.models.metaschema import RegistrationSchema

from .base import (
    expand_listed_key, get_sources_for_key, find_schema_question, is_special_key, is_key_present, get_value, resolve_array_index
)


logger = logging.getLogger(__name__)

columns_default = [
    ('#.id', '#ID', '#', '#', ''),
    ('.uri', 'URI', '', '', ''),
    ('.cnri', '.CNRI', '', '', ''),
    ('.doi_ra', '.DOI_RA', '', '', ''),
    ('.doi', '.DOI', '', '', ''),
    ('.edit_mode', 'Keep/Upgrade Version', '', 'Required', 'Keep'),
]


def _generate_file_columns(index, download_file_name, download_file_type):
    columns = []
    columns.append((
        f'.file_path[{index}]',
        f'.ファイルパス[{index}]',
        '',
        'Allow Multiple',
        f'files/{download_file_name}'
    ))
    return columns

def _to_columns(full_key, value, weko_key_counts=None):
    if f'{full_key}.__value__' in weko_key_counts:
        if weko_key_counts[f'{full_key}.__value__'] != value:
            raise ValueError(f'Different values to the same key are detected: {value}, {weko_key_counts[f"{full_key}.__value__"]}')
        logger.debug(f'Skipped duplicated item: {full_key}')
        return []
    weko_key_counts[f'{full_key}.__value__'] = value
    return [
        (
            full_key,
            '',
            '',
            '',
            value,
        )
    ]

def _get_columns(file_metadata, weko_key_prefix, weko_props, weko_key_counts=None, commonvars=None, schema=None):
    if isinstance(weko_props, str):
        value = get_value(file_metadata, weko_props, commonvars=commonvars, schema=schema)
        return _to_columns(weko_key_prefix, value, weko_key_counts=weko_key_counts)
    columns = []
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
                columns += _get_columns(
                    file_metadata,
                    full_key,
                    item,
                    weko_key_counts=weko_key_counts,
                    commonvars=commonvars,
                    schema=schema,
                )
                continue
            value = get_value(file_metadata, item, commonvars=commonvars, schema=schema)
            columns += _to_columns(full_key, value, weko_key_counts=weko_key_counts)
    return columns

def write_csv(user, f, target_index, download_file_names, schema_id, file_metadatas, project_metadatas):
    from ..models import RegistrationMetadataMapping
    schema = RegistrationSchema.objects.get(_id=schema_id)
    mapping_def = RegistrationMetadataMapping.objects.filter(
        registration_schema_id=schema._id,
        filename__in=['index.csv', None],
    ).first()
    if mapping_def is None:
        raise ValueError(f'No mapping definition: {schema_id}')
    logger.debug(f'Mappings: {mapping_def.rules}')
    for i, file_metadata in enumerate(file_metadatas):
        logger.debug(f'File metadata #{i}: {file_metadata}')
    for i, project_metadata in enumerate(project_metadatas):
        logger.debug(f'Project metadata #{i}: {project_metadata}')
    mapping_metadata = mapping_def.rules['@metadata']
    itemtype_metadata = mapping_metadata['itemtype']
    header = ['#ItemType', itemtype_metadata['name'], itemtype_metadata['schema']]

    columns = [('.publish_status', '.PUBLISH_STATUS', '', 'Required', 'private')]
    columns.append(('.metadata.path[0]', '.IndexID[0]', '', 'Allow Multiple', target_index.identifier))
    columns.append(('.pos_index[0]', '.POS_INDEX[0]', '', 'Allow Multiple', target_index.title))
    for i, (download_file_name, download_file_type) in enumerate(download_file_names):
        columns += _generate_file_columns(i, download_file_name, download_file_type)

    mappings = expand_listed_key(mapping_def.rules)

    weko_key_counts = {}
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
                columns += _get_columns(
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
                    columns += _get_columns(
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
                columns += _get_columns(
                    target_data,
                    '',
                    weko_mapping,
                    weko_key_counts=weko_key_counts,
                    commonvars=commonvars,
                    schema=question_schema,
                )
                continue
            raise ValueError(f'Unexpected type: {weko_mapping["@type"]}')

    columns += columns_default
    logger.debug(f'Columns: {columns}')

    cf = csv.writer(f)
    cf.writerow(header)
    cf.writerow([c for c, _, _, _, _ in columns])
    cf.writerow([c for _, c, _, _, _ in columns])
    cf.writerow([c for _, _, c, _, _ in columns])
    cf.writerow([c for _, _, _, c, _ in columns])
    cf.writerow([c for _, _, _, _, c in columns])
