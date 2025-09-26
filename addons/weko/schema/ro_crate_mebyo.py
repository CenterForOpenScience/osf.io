import json
from typing import Any, Dict, List, Tuple, Type, Union

# 日本語・英語対応が必要なプロパティの言語コード
LANG_LIST: List[str] = ['ja','en']
META_GROUP_PREFIX: Dict[str, str] = {
    'txt':'d-txt-group',
    'exl':'d-exl-group',
    'img':'d-image-group',
    'abt':'d-any-group'
}

# (prop_name, type もしくは言語対応必要なプロパティの場合は言語コード): [対応する metadata の key の list]
MAPPING: Dict[Tuple[str, Union[Type[str], Type[int], Type[float]]], List[str]] = {
    ('ams:objectOfMeasurement', 'ja'):['d-msr-object-of-measurement-jp'],
    ('ams:objectOfMeasurement', 'en'):['d-msr-object-of-measurement-en'],
    ('ams:targetOrgansForMeasurement', str):['d-msr-target-organs-for-measurement'],
    ('ams:dataType', 'ja'):['d-msr-data-type-jp'],
    ('ams:dataType', 'en'):['d-msr-data-type-en'],
    ('ams:classificationOfMeasuringDevices', 'ja'):['d-msr-classification-of-measuring-devices-jp'],
    ('ams:classificationOfMeasuringDevices', 'en'):['d-msr-classification-of-measuring-devices-en'],
    ('rdm:instrument', 'schema:Thing'):['d-msr-measuring-device-name'],
    ('schema:name', 'ja'):['Measuring-device-name', 'Metadata-item-name', 'Name-of-term'],
    ('schema:name', 'en'):['Measuring-device-name-en', 'Metadata-item-name-en', 'Name-of-term-en'],
    ('rdm:protocol', 'schema:HowTo'):['d-msr-procedure'],
    ('schema:text', 'ja'):['Procedure'],
    ('schema:text', 'en'):['Procedure-en'],
    ('ams:additionalMetadata', 'PropertyValue'):['d-msr-user-defined-metadata-items', 't-abt-user-defined-metadata-items'],
    ('schema:value', 'ja'):['value-or-content'],
    ('schema:value', 'en'):['value-or-content-en'],
    ('ams:measurementRemarks', 'ja'):['d-msr-remarks-jp'],
    ('ams:measurementRemarks', 'en'):['d-msr-remarks-en'],
    ('ams:descriptionOfFolder', 'rdm:MetadataDocument'):['d-fol-Structure-or-descriptions-of-folders-jp'],
    ('ams:folderName', str):['folder-name'],
    ('rdm:description', 'ja'):['description-of-folder', 'd-txt-description-jp', 'd-exl-description-jp', 'd-img-description-jp', 'd-abt-description-jp'],
    ('rdm:description', 'en'):['description-of-folder-en', 'd-txt-description-en', 'd-exl-description-en', 'd-img-description-en', 'd-abt-description-en'],
    ('ams:contents', str):['contents'],
    ('ams:folderRemarks','ja'):['d-d-fol-remarks-jp'],
    ('ams:folderRemarks','en'):['d-d-fol-remarks-en'],
    ('ams:descriptionOfTextFile', 'rdm:MetadataDocument'):['d-txt-group'],
    ('ams:descriptionOfExcelFile', 'rdm:MetadataDocument'):['d-exl-group'],
    ('ams:descriptionOfImageFile', 'rdm:MetadataDocument'):['d-image-group'],
    ('ams:descriptionOfOtherFile', 'rdm:MetadataDocument'):['d-any-group'],
    ('ams:fileName', str):['d-txt-file-name-convention-file-extension', 'd-exl-file-name-convention-file-extension','d-img-file-name-convention-file-extension', 'd-abt-file-name-convention-file-extension', 'file-name-convention-file-extension'],
    ('ams:rowItem', 'schema:ListItem'):['d-txt-description-of-row', 'd-exl-description-of-row'],
    ('schema:position', 'ja'):['Position-of-row', 'Position-of-column'],
    ('schema:position', 'en'):['Position-of-row-en', 'Position-of-column-en'],
    ('schema:description', 'ja'):['Description-of-term'],
    ('schema:description', 'en'):['Description-of-term-en'],
    ('ams:columnItem', 'schema:ListItem'):['d-txt-description-of-column', 'd-exl-description-of-column'],
    ('ams:dataPreprocessing', 'ja'):['d-txt-data-preprocessing-jp', 'd-exl-data-preprocessing-jp', 'd-img-data-preprocessing-jp', 'd-abt-data-preprocessing-jp'],
    ('ams:dataPreprocessing', 'en'):['d-txt-data-preprocessing-en', 'd-exl-data-preprocessing-en', 'd-img-data-preprocessing-en', 'd-abt-data-preprocessing-en'],
    ('ams:isTemporalMeasurementData', str):['d-txt-temporal-measurement-data', 'd-exl-temporal-measurement-data', 'd-img-temporal-measurement-data', 'd-abt-temporal-measurement-data'],
    ('ams:numberOfRows', int):['d-txt-number-of-rows', 'd-exl-number-of-rows', 'd-abt-number-of-rows'],
    ('ams:numberOfColumns', int):['d-txt-number-of-columns', 'd-exl-number-of-columns', 'd-abt-number-of-columns'],
    ('ams:approximateNumberOfSimilarFiles ', str):['d-txt-approximate-number-of-similar-files', 'd-exl-approximate-number-of-similar-files', 'd-img-approximate-number-of-similar-files', 'd-abt-approximate-number-of-similar-files'],
    ('ams:delimiter', str):['t-txt-delimiter','t-abt-delimiter'],
    ('ams:characterCode', str):['t-txt-character-code', 't-abt-character-code'],
    ('ams:remarks', 'ja'):['t-txt-remarks-jp', 't-exl-remarks-jp', 't-img-remarks-jp', 't-abt-remarks-jp'],
    ('ams:remarks', 'en'):['t-txt-remarks-en', 't-exl-remarks-en', 't-img-remarks-en', 't-abt-remarks-en'],
    ('ams:widthPixels', int):['d-img-pixel-width', 'd-abt-pixel-width'],
    ('ams:heightPixels', int):['d-img-pixel-height', 'd-abt-pixel-height'],
    ('ams:resolutionHorizontal', str):['d-img-resolution-horizontal', 'd-abt-resolution-horizontal'],
    ('ams:resolutionVertical', str):['d-img-resolution-vertical', 'd-abt-resolution-vertical'],
    ('ams:numberOfColorInformation', str):['t-img-Color-Monochrome', 't-abt-Color-Monochrome'],
    ('ams:colorBits', str):['t-img-number-of-color-bit', 't-abt-number-of-color-bit'],
    ('ams:compressedFormat', str):['t-img-compression-format', 't-abt-compression-format'],
    ('ams:imageType', str):['t-img-image-type', 't-abt-image-type'],
    ('ams:fileType', str):['t-abt-text/binary'],
    ('ams:structureInformation', 'rdm:MetadataDocument'):['grdm-file:d-txt-file-name-convention-file-extension', 'grdm-file:d-exl-file-name-convention-file-extension', 'grdm-file:d-img-file-name-convention-file-extension', 'grdm-file:d-abt-file-name-convention-file-extension'],
    ('ams:storageFolder', str):['storage-folder'],
}

MAPPING_DICT: Dict[str, Dict[str, str]] = {
    key: {"prop_name": prop, "prop_type": ptype}
    for (prop, ptype), keys in MAPPING.items()
    for key in keys
}

def _deep_json_loads(obj: Any)-> Any: 
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

def _create_new_entity(entity_id:str, entity_type:str, index:int = 0) ->Any:
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
        raise ValueError(f'Value {value} of metadata must be list, dict or scholar.')

def _add_metadata_entity(index:int, resource_metadata:Any, file_prefix:str = '') -> List[Dict[str, Any]]:
    base_entity = _create_new_entity('_:ams:ResourceMetadataDocument_','ams:ResourceMetadataDocument',index)
    entity_list = [base_entity]

    for key, meta in resource_metadata.items():
        if key in MAPPING_DICT and meta['value']:
            _add_property_to_entity(entity_list, base_entity, key, meta['value'], f'{file_prefix }{key}')

    # skip empty entity (only has @id and @type)
    if len(base_entity) == 2:
        return []
    return entity_list

def generate_dataset_metadata(project_metadatas: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    '''未病スキーマのデータセットメタデータ・ファイルメタデータをエンティティ化'''
    if len(project_metadatas) !=1:
        raise ValueError('Choose 1 project metadata to export.')
    entities =[]
    project_metadata = _deep_json_loads(project_metadatas[0])
    root_propeties = {}
    index = 1

    # add dataset metadata entity
    dataset_metadata_entities = _add_metadata_entity(index, project_metadata)
    entities += dataset_metadata_entities
    if len(dataset_metadata_entities) > 0:
        root_propeties['ams:datasetMetadata'] = {
            '@id':f'_:ResourceMetadataDocument{index}'
            }
        index += 1

    # add file metadata entity
    if len(project_metadata['grdm-files']['value']) > 0:
        root_propeties['ams:fileMetadata'] = []
        for i, original_file_metadata in enumerate(project_metadata['grdm-files']['value']):
            root_propeties['ams:fileMetadata'].append({
                '@id':f'_:ResourceMetadataDocument{index}'
            })

            file_metadata = {
                key[10:]:value for key, value in original_file_metadata['metadata'].items()
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

            file_metadata_entities = _add_metadata_entity(index, file_metadata, f'file{ i + 1 }_')
            entities += file_metadata_entities
            index += 1

    return entities, root_propeties
