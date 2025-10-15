import json
from typing import Any, Dict, List, Tuple, Union

from .constants_mebyo import LANG_LIST, META_GROUP_PREFIX, MAPPING

MAPPING_DICT: Dict[str, Dict[str, str]] = {
    key: {'prop_name': prop, 'prop_type': ptype}
    for (prop, ptype), keys in MAPPING.items()
    for key in keys
}

def _deep_json_loads(obj: Any) -> Any:
    '''一部メタデータに str が残っているため、再帰的に JSON をデコードする'''
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            return _deep_json_loads(parsed)
        except (json.JSONDecodeError, TypeError):
            return obj
    elif isinstance(obj, dict):
        return {k: _deep_json_loads(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_json_loads(v) for v in obj]
    else:
        return obj

def _create_new_entity(entity_id: str, entity_type: str, index: int = 0) -> Any:
    if entity_id.startswith('_:'):
        entity_id = entity_id[2:]

    local_id = f'_:{entity_id}{index if index else ""}'
    new_entity = {
        '@id': local_id,
        '@type': entity_type
    }

    return new_entity

def _add_scalar_property(
    base_entity: Dict[str, Any],
    prop_name: str,
    value: Union[str, int, float]
) -> None:
    base_entity[prop_name] = value

def _add_lang_property(
    entity_list: List[Dict[str, Any]],
    base_entity: Dict[str, Any],
    prop_name: str,
    prop_type: str,
    value: str,
    entity_id: str
) -> None:
    base_entity.setdefault(prop_name, [])
    new_entity = _create_new_entity(entity_id, 'PropertyValue')
    new_entity['language'] = prop_type
    new_entity['value'] = value
    entity_list.append(new_entity)

    base_entity[prop_name].append({'@id': new_entity['@id']})

def _add_list_property(
    entity_list: List[Dict[str, Any]],
    base_entity: Dict[str, Any],
    prop_name: str,
    child_type: str,
    value: List[Dict[str, Any]],
    entity_id: str
) -> None:
    base_entity.setdefault(prop_name, [])
    for i, child in enumerate(value):
        new_entity = _create_new_entity(entity_id, child_type, i + 1)
        entity_list.append(new_entity)
        base_entity[prop_name].append({'@id': new_entity['@id']})
        for k, v in child.items():
            _add_property_to_entity(entity_list, new_entity, k, v, f'{new_entity["@id"]}_{k}')

def _add_dict_property(
    entity_list: List[Dict[str, Any]],
    base_entity: Dict[str, Any],
    prop_name: str,
    child_type: str,
    value: Dict[str, Any],
    entity_id: str
) -> None:
    new_entity = _create_new_entity(entity_id, child_type)
    base_entity.setdefault(prop_name, {'@id': new_entity['@id']})
    for k, v in value.items():
        _add_property_to_entity(entity_list, new_entity, k, v, f'{new_entity["@id"]}_{k}')

def _add_property_to_entity(
    entity_list: List[Dict[str, Any]],
    base_entity: Dict[str, Any],
    key: str,
    value: Any,
    entity_id: str
) -> None:
    if key not in MAPPING_DICT:
        raise ValueError(f'Mapping to {key} is not defined.')

    mapping = MAPPING_DICT[key]
    prop_name = mapping['prop_name']
    prop_type = mapping['prop_type']

    if prop_type in [str, int, float]:
        _add_scalar_property(base_entity, prop_name, value)

    elif mapping['prop_type'] in LANG_LIST and isinstance(value, str):
        _add_lang_property(entity_list, base_entity, prop_name, prop_type, value, entity_id)

    elif isinstance(value, list):
        _add_list_property(entity_list, base_entity, prop_name, prop_type, value, entity_id)

    elif isinstance(value, dict):
        _add_dict_property(entity_list, base_entity, prop_name, prop_type, value, entity_id)

    else:
        raise ValueError(f'Value {value} of metadata must be list, dict or scalar.')

def _add_metadata_entity(index: int, resource_metadata: Any, file_prefix: str = '') -> List[Dict[str, Any]]:
    base_entity = _create_new_entity('_:ams:ResourceMetadataDocument', 'ams:ResourceMetadataDocument', index)
    entity_list = [base_entity]

    for key, meta in resource_metadata.items():
        if key in MAPPING_DICT and meta['value']:
            _add_property_to_entity(entity_list, base_entity, key, meta['value'], f'{file_prefix}{key}')

    # skip empty entity (only has @id and @type)
    if len(base_entity) == 2:
        return []
    return entity_list

def generate_dataset_metadata(project_metadatas: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    '''未病スキーマのデータセットメタデータ・ファイルメタデータをエンティティ化'''
    if len(project_metadatas) != 1:
        raise ValueError('Choose 1 project metadata to export.')
    entities = []
    project_metadata = _deep_json_loads(project_metadatas[0])
    root_properties = {}
    index = 1

    # add dataset metadata entity
    dataset_metadata_entities = _add_metadata_entity(index, project_metadata)
    entities += dataset_metadata_entities
    if len(dataset_metadata_entities) > 0:
        root_properties['ams:datasetMetadata'] = {
            '@id': f'_:ResourceMetadataDocument{index}'
        }
        index += 1

    # add file metadata entity
    if len(project_metadata['grdm-files']['value']) > 0:
        root_properties['ams:fileMetadata'] = []
        for i, original_file_metadata in enumerate(project_metadata['grdm-files']['value']):
            root_properties['ams:fileMetadata'].append({
                '@id': f'_:ResourceMetadataDocument{index}'
            })

            file_metadata = {
                key[10:]: value for key, value in original_file_metadata['metadata'].items()
            }

            # dataset metadata に合わせる形で JSON を修正
            for prefix, prop in META_GROUP_PREFIX.items():
                meta_entity = {k: v['value'] for k, v in list(file_metadata.items()) if f'-{prefix}-' in k}
                for k in meta_entity:
                    file_metadata.pop(k)

                # file-convention 特殊対応
                for key in list(meta_entity):
                    if key.endswith('file-name-convention-file-extension'):
                        meta_entity[f'grdm-file:{key}'] = meta_entity.pop(key)

                file_metadata[prop] = {'value': [meta_entity]}

            file_metadata_entities = _add_metadata_entity(index, file_metadata, f'file{i + 1}_')
            entities += file_metadata_entities
            index += 1

    return entities, root_properties
