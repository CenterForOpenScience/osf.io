from datetime import datetime
import json
import logging
import re

from jinja2 import Environment

from ..mappings.utils import JINJA2_FILTERS


logger = logging.getLogger(__name__)


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
            options = []
            for o in schema['options']:
                if isinstance(o, str):
                    options.append({'text': o})
                elif isinstance(o, dict):
                    options.append(o)
                else:
                    logger.debug(f'Unexpected option type: {type(o)} for value={v}')
                filtered_options = [
                    o
                    for o in options
                    if o.get('text', None) == v or (not v and o.get('default', False))
                ]
            if len(filtered_options) == 0:
                logger.debug(f'No suitable options: value={v}, schema={schema}')
            else:
                option = filtered_options[0]
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

def get_value(file_metadata, text, commonvars=None, schema=None):
    values = _get_item_variables(file_metadata, schema=schema)
    if commonvars is not None:
        values.update(commonvars)
    if text in values and isinstance(values[text], list):
        return values[text]
    env = Environment(autoescape=False)
    for name, filter_ in JINJA2_FILTERS.items():
        env.filters[name] = filter_
    template = env.from_string(text)
    return template.render(**values)

def is_key_present(file_metadata, item, commonvars=None, schema=None):
    if not isinstance(item, dict):
        return True
    present_expression = item.get('@createIf', None)
    if present_expression is None:
        return True
    value = get_value(file_metadata, present_expression, commonvars=commonvars, schema=schema)
    logger.debug(f'Column check: "{present_expression}" => "{value}"')
    return value

def _get_item_metadata_key(key):
    m = re.match(r'^(.+)\[[0-9]*\]$', key)
    if m:
        return _get_item_metadata_key(m.group(1))
    return key

def find_schema_question(schema, qid):
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
    from ..models import RegistrationMetadataMapping
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

def _get_common_variables(file_metadata_data, schema, target_index, skip_empty=False):
    r = {
        'nowdate': datetime.now().strftime('%Y-%m-%d'),
        'index_id': str(target_index.identifier),
        'index_title': target_index.title,
    }
    for key in file_metadata_data.keys():
        if skip_empty and not file_metadata_data[key].get('value', ''):
            continue
        values = _get_item_variables(
            file_metadata_data[key],
            schema=find_schema_question(schema.schema, key),
        )
        key_ = key.replace('-', '_').replace(':', '_').replace('.', '_')
        r.update(dict([(f'{key_}_{k}', v) for k, v in values.items()]))
    return r

def resolve_array_index(weko_key_counts, key):
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

def expand_listed_key(mappings):
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

def get_sources_for_key(
    user, target_index, file_metadatas, download_file_names, project_metadatas, schema, key,
):
    common_file_metadata_datas = sum([
        [item['data'] for item in file_metadata['items'] if item['schema'] == schema._id]
        for file_metadata in file_metadatas
    ], [])
    common_project_metadatas = project_metadatas
    common_file_metadata_data = _concatenate_sources(common_file_metadata_datas)
    common_file_commonvars = _get_common_variables(
        common_file_metadata_data,
        schema,
        target_index,
        skip_empty=True,
    )
    common_project_metadata = _concatenate_sources(common_project_metadatas)
    common_project_commonvars = _get_common_variables(
        common_project_metadata,
        schema,
        target_index,
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
            commonvars = _get_common_variables(file_metadata_data, schema, target_index, True)
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
            commonvars = _get_common_variables(project_metadata, schema, target_index, True)
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
        target_index,
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

def is_special_key(key):
    return key in ['_', '@files', '@projects', '@agent']
