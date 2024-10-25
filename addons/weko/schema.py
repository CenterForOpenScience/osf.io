import csv
from datetime import datetime
import json
import logging
import re

from jinja2 import Environment

from osf.models.metaschema import RegistrationSchema
from .mappings.utils import JINJA2_FILTERS


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
    columns.append((f'.file_path[{index}]', f'.ファイルパス[{index}]', '', 'Allow Multiple', download_file_name))
    return columns

def _get_metadata_value(file_metadata_data, item, lang, index):
    assert 'type' in item, item
    if item['type'] == 'const':
        if 'depends' in item:
            value = _get_metadata_value(file_metadata_data, item['depends'], lang, index)
            if not value:
                return ''
        return item['value']
    key = f'grdm-file:{item["key"]}'
    if lang is not None:
        key += f'.{lang}'
    if key not in file_metadata_data:
        return ''
    value = file_metadata_data[key]['value']
    if item['type'] == 'property':
        return value
    if item['type'] == 'jsonproperty':
        logger.debug(f'jsonproperty: {value}')
        return json.loads(value)[index][item['value']]
    raise KeyError(item['type'])

def _get_item_variables(file_metadata, schema=None):
    values = {
        'value': '',
    }
    if file_metadata is None:
        return values
    if 'value' in file_metadata:
        v = file_metadata['value']
        if schema is not None and 'options' in schema:
            options = [
                o
                for o in schema['options']
                if o.get('text', None) == v or (not v and o.get('default', False))
            ]
            if len(options) == 0:
                logger.debug(f'No suitable options: value={v}, schema={schema}')
            else:
                option = options[0]
                v = option['text']
                if 'tooltip' in option:
                    values['tooltip'] = option['tooltip']
                    langs = option['tooltip'].split('|')
                    if len(langs) > 1:
                        for i, s in enumerate(langs):
                            values[f'tooltip_{i}'] = s
                    else:
                        for i in range(2):
                            values[f'tooltip_{i}'] = option['tooltip']
        values['value'] = v
    if 'object' in file_metadata:
        o = file_metadata['object']
        values.update(_get_object_variables(o, 'object_'))
    return values

def _get_object_variables(o, prefix):
    values = {}
    for k, v in o.items():
        key_ = k.replace('-', '_').replace(':', '_').replace('.', '_')
        if isinstance(v, dict):
            values.update(_get_object_variables(v, f'{prefix}{key_}_'))
            continue
        values[f'{prefix}{key_}'] = v
    return values

def _get_value(file_metadata, text, commonvars=None, schema=None):
    values = _get_item_variables(file_metadata, schema=schema)
    if commonvars is not None:
        values.update(commonvars)
    env = Environment(autoescape=False)
    for name, filter_ in JINJA2_FILTERS.items():
        env.filters[name] = filter_
    template = env.from_string(text)
    return template.render(**values)

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

def _is_column_present(file_metadata, item, commonvars=None, schema=None):
    if not isinstance(item, dict):
        return True
    present_expression = item.get('@createIf', None)
    if present_expression is None:
        return True
    value = _get_value(file_metadata, present_expression, commonvars=commonvars, schema=schema)
    logger.debug(f'Column check: "{present_expression}" => "{value}"')
    return value

def _get_columns(file_metadata, weko_key_prefix, weko_props, weko_key_counts=None, commonvars=None, schema=None):
    if isinstance(weko_props, str):
        value = _get_value(file_metadata, weko_props, commonvars=commonvars, schema=schema)
        return _to_columns(weko_key_prefix, value, weko_key_counts=weko_key_counts)
    columns = []
    for key in sorted(weko_props.keys()):
        items = weko_props[key]
        if key.startswith('@'):
            continue
        if not isinstance(items, list):
            items = [items]
        for item in items:
            if not _is_column_present(file_metadata, item, commonvars=commonvars, schema=schema):
                continue
            full_key = _resolve_array_index(weko_key_counts, f'{weko_key_prefix}.{key}')
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
            value = _get_value(file_metadata, item, commonvars=commonvars, schema=schema)
            columns += _to_columns(full_key, value, weko_key_counts=weko_key_counts)
    return columns

def _get_item_metadata_key(key):
    m = re.match(r'^(.+)\[[0-9]*\]$', key)
    if m:
        return _get_item_metadata_key(m.group(1))
    return key

def _find_schema_question(schema, qid):
    if 'pages' not in schema:
        return
    for page in schema['pages']:
        if 'questions' not in page:
            continue
        for question in page['questions']:
            if question['qid'] == qid:
                return question
    logger.warning(f'Question {qid} not found: schema={schema}')
    raise KeyError(f'Question {qid} not found')

def get_available_schema_id(file_metadata):
    from .models import RegistrationMetadataMapping
    available_schema_ids = [
        mapping.registration_schema_id
        for mapping in RegistrationMetadataMapping.objects.all()
    ]
    items = [
        item
        for item in file_metadata['items']
        if item.get('active', False) and item.get('schema', None) in available_schema_ids
    ]
    if len(items):
        return items[0]['schema']
    items = [
        item
        for item in file_metadata['items']
        if item.get('schema', None) in available_schema_ids
    ]
    if len(items):
        return items[0]['schema']
    raise ValueError(f'Available schemas not found: {file_metadata}')

def _get_common_variables(file_metadata_data, schema, skip_empty=False):
    r = {
        'nowdate': datetime.now().strftime('%Y-%m-%d'),
    }
    for key in file_metadata_data.keys():
        if skip_empty and not file_metadata_data[key].get('value', ''):
            continue
        values = _get_item_variables(
            file_metadata_data[key],
            schema=_find_schema_question(schema.schema, key),
        )
        key_ = key.replace('-', '_').replace(':', '_').replace('.', '_')
        r.update(dict([(f'{key_}_{k}', v) for k, v in values.items()]))
    return r

def _resolve_array_index(weko_key_counts, key):
    m = re.match(r'^(.+)\[(.*)\]$', key)
    if not m:
        return key
    key_body = m.group(1)
    index_id = m.group(2)
    weko_key_ids = weko_key_counts.get(key_body, None)
    if weko_key_ids is None:
        weko_key_ids = []
    if not index_id:
        weko_key_count = len(weko_key_ids)
        weko_key_counts[key_body] = weko_key_ids + [None]
        return f'{key_body}[{weko_key_count}]'
    matched = [i for i, weko_key_id in enumerate(weko_key_ids) if weko_key_id == index_id]
    if len(matched) == 0:
        # New key
        weko_key_count = len(weko_key_ids)
        weko_key_counts[key_body] = weko_key_ids + [index_id]
        return f'{key_body}[{weko_key_count}]'
    # Existing key
    weko_key_count = matched[0]
    return f'{key_body}[{weko_key_count}]'

def _expand_listed_key(mappings):
    r = {}
    for k, v in mappings.items():
        if k == '@metadata':
            continue
        for e in k.split():
            r[e] = v
    return r

def _resolve_duplicated_values(items):
    if len(items) == 0:
        raise ValueError('No items')
    if len(items) == 1:
        return items[0]['value']
    values = [json.dumps(item['value']) for item in items]
    if len(set(values)) == 1:
        return items[0]['value']
    return None

def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and len(value) == 0:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, dict):
        for v in value.values():
            if not _is_empty(v):
                return False
        return True
    return False

def _concatenate_sources(metadatas, check_duplicates=[]):
    if len(metadatas) == 0:
        return {}
    keys = sorted(set(sum([list(m.keys()) for m in metadatas], [])))
    r = {}
    for key in keys:
        items = [metadata[key] for metadata in metadatas if key in metadata]
        if len(items) == 0:
            continue
        empty_items = [item for item in items if _is_empty(item.get('value', ''))]
        non_empty_items = [item for item in items if not _is_empty(item.get('value', ''))]
        if len(non_empty_items) == 0:
            r[key] = empty_items[0]
            continue
        if len(non_empty_items) == 1:
            r[key] = non_empty_items[0]
            continue
        value = _resolve_duplicated_values(non_empty_items)
        if value is not None:
            r[key] = {
                'value': value,
            }
            continue
        if key not in check_duplicates:
            continue
        non_empty_values = [item['value'] for item in non_empty_items]
        raise ValueError(f'Duplicated values for key: {key}, {non_empty_values}')
    return r

def _has_serializable_attr(object, k):
    try:
        value = getattr(object, k)
        json.dumps(value)
        return True
    except Exception:
        return False

def _get_sources_for_key(user, file_metadatas, download_file_names, project_metadatas, schema, key):
    common_file_metadata_datas = sum([
        [item['data'] for item in file_metadata['items'] if item['schema'] == schema._id]
        for file_metadata in file_metadatas
    ], [])
    common_project_metadatas = project_metadatas
    common_file_metadata_data = _concatenate_sources(common_file_metadata_datas)
    common_file_commonvars = _get_common_variables(
        common_file_metadata_data,
        schema,
        skip_empty=True,
    )
    common_project_metadata = _concatenate_sources(common_project_metadatas)
    common_project_commonvars = _get_common_variables(
        common_project_metadata,
        schema,
        skip_empty=True,
    )
    if key == '@files':
        if len(file_metadatas) != len(download_file_names):
            raise ValueError(f'File metadata count mismatch: {len(file_metadatas)} != {len(download_file_names)}')
        r = []
        for file_metadata, (download_file_name, download_file_type) in zip(file_metadatas, download_file_names):
            file_metadata_items = [item for item in file_metadata['items'] if item['schema'] == schema._id]
            if len(file_metadata_items) == 0:
                raise ValueError(f'Schema not found: {file_metadata}, {schema._id}')
            file_metadata_data = file_metadata_items[0]['data']
            commonvars = _get_common_variables(file_metadata_data, schema)
            commonvars.update(common_project_commonvars)
            file_metadata_data_ = {
                'filename': download_file_name,
                'format': download_file_type,
            }
            file_metadata_data_.update(dict([
                (k, v.get('value', ''))
                for k, v in file_metadata_data.items()
            ]))
            r.append(({
                '@files': {
                    'value': file_metadata_data_,
                },
            }, commonvars))
        return r
    if key == '@projects':
        r = []
        for project_metadata in project_metadatas:
            commonvars = _get_common_variables(project_metadata, schema)
            commonvars.update(common_file_commonvars)
            r.append(({
                '@projects': {
                    'value': project_metadata,
                },
            }, commonvars))
        return r
    commonvars = _get_common_variables(
        common_file_metadata_data,
        schema,
    )
    commonvars.update(common_project_commonvars)
    if key == '@agent':
        user_metadata = dict([
            (k, getattr(user, k))
            for k in dir(user)
            if _has_serializable_attr(user, k)
        ])
        logger.info(f'@agent: {user_metadata}')
        return [(
            {
                '@agent': {
                    'value': user_metadata,
                },
            },
            commonvars,
        )]
    return [(
        _concatenate_sources(
            common_project_metadatas + common_file_metadata_datas,
            check_duplicates=[key],
        ),
        commonvars,
    )]

def _is_special_key(key):
    return key in ['_', '@files', '@projects', '@agent']

def write_csv(user, f, target_index, download_file_names, schema_id, file_metadatas, project_metadatas):
    from .models import RegistrationMetadataMapping
    schema = RegistrationSchema.objects.get(_id=schema_id)
    mapping_def = RegistrationMetadataMapping.objects.get(
        registration_schema_id=schema._id,
    )
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

    mappings = _expand_listed_key(mapping_def.rules)

    weko_key_counts = {}
    for key in sorted(mappings.keys()):
        for source, commonvars in _get_sources_for_key(
            user, file_metadatas, download_file_names, project_metadatas, schema, key
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
            question_schema = _find_schema_question(schema.schema, key) if not _is_special_key(key) else None
            if key == '_' or weko_mapping.get('@type', None) == 'string':
                if not _is_column_present(
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
                    if not _is_column_present(
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
                if not _is_column_present(
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
