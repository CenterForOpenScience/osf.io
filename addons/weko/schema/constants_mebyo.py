from typing import Dict, List, Tuple, Type, Union

# スキーマ名
MEBYO_SCHEMA_NAME: str = 'ムーンショット目標2データベース（未病DB）のメタデータ登録'

# 日本語・英語対応が必要なプロパティの言語コード
LANG_LIST: List[str] = ['ja', 'en']

# ファイルメタデータの配列化に使用するプロパティ名
META_GROUP_PREFIX: Dict[str, str] = {
    'txt': 'd-txt-group',
    'exl': 'd-exl-group',
    'img': 'd-image-group',
    'abt': 'd-any-group'
}

# (prop_name, type もしくは言語対応必要なプロパティの場合は言語コード): [対応する metadata の key の list]
MAPPING: Dict[Tuple[str, Union[Type[str], Type[int], Type[float]]], List[str]] = {
    ('ams:objectOfMeasurement', 'ja'): ['d-msr-object-of-measurement-jp'],
    ('ams:objectOfMeasurement', 'en'): ['d-msr-object-of-measurement-en'],
    ('ams:targetOrgansForMeasurement', str): ['d-msr-target-organs-for-measurement'],
    ('ams:dataType', 'ja'): ['d-msr-data-type-jp'],
    ('ams:dataType', 'en'): ['d-msr-data-type-en'],
    ('ams:classificationOfMeasuringDevices', 'ja'): ['d-msr-classification-of-measuring-devices-jp'],
    ('ams:classificationOfMeasuringDevices', 'en'): ['d-msr-classification-of-measuring-devices-en'],
    ('rdm:instrument', 'schema:Thing'): ['d-msr-measuring-device-name'],
    ('schema:name', 'ja'): ['Measuring-device-name', 'Metadata-item-name', 'Name-of-term'],
    ('schema:name', 'en'): ['Measuring-device-name-en', 'Metadata-item-name-en', 'Name-of-term-en'],
    ('rdm:protocol', 'schema:HowTo'): ['d-msr-procedure'],
    ('schema:text', 'ja'): ['Procedure'],
    ('schema:text', 'en'): ['Procedure-en'],
    ('ams:additionalMetadata', 'PropertyValue'): ['d-msr-user-defined-metadata-items', 't-abt-user-defined-metadata-items'],
    ('schema:value', 'ja'): ['value-or-content'],
    ('schema:value', 'en'): ['value-or-content-en'],
    ('ams:measurementRemarks', 'ja'): ['d-msr-remarks-jp'],
    ('ams:measurementRemarks', 'en'): ['d-msr-remarks-en'],
    ('ams:descriptionOfFolder', 'rdm:MetadataDocument'): ['d-fol-Structure-or-descriptions-of-folders-jp'],
    ('ams:folderName', str): ['folder-name'],
    ('rdm:description', 'ja'): ['description-of-folder', 'd-txt-description-jp', 'd-exl-description-jp', 'd-img-description-jp', 'd-abt-description-jp'],
    ('rdm:description', 'en'): ['description-of-folder-en', 'd-txt-description-en', 'd-exl-description-en', 'd-img-description-en', 'd-abt-description-en'],
    ('ams:contents', str): ['contents'],
    ('ams:folderRemarks', 'ja'): ['d-d-fol-remarks-jp'],
    ('ams:folderRemarks', 'en'): ['d-d-fol-remarks-en'],
    ('ams:descriptionOfTextFile', 'rdm:MetadataDocument'): ['d-txt-group'],
    ('ams:descriptionOfExcelFile', 'rdm:MetadataDocument'): ['d-exl-group'],
    ('ams:descriptionOfImageFile', 'rdm:MetadataDocument'): ['d-image-group'],
    ('ams:descriptionOfOtherFile', 'rdm:MetadataDocument'): ['d-any-group'],
    ('ams:fileName', str): ['d-txt-file-name-convention-file-extension', 'd-exl-file-name-convention-file-extension', 'd-img-file-name-convention-file-extension', 'd-abt-file-name-convention-file-extension', 'file-name-convention-file-extension'],
    ('ams:rowItem', 'schema:ListItem'): ['d-txt-description-of-row', 'd-exl-description-of-row'],
    ('schema:position', 'ja'): ['Position-of-row', 'Position-of-column'],
    ('schema:position', 'en'): ['Position-of-row-en', 'Position-of-column-en'],
    ('schema:description', 'ja'): ['Description-of-term'],
    ('schema:description', 'en'): ['Description-of-term-en'],
    ('ams:columnItem', 'schema:ListItem'): ['d-txt-description-of-column', 'd-exl-description-of-column'],
    ('ams:dataPreprocessing', 'ja'): ['d-txt-data-preprocessing-jp', 'd-exl-data-preprocessing-jp', 'd-img-data-preprocessing-jp', 'd-abt-data-preprocessing-jp'],
    ('ams:dataPreprocessing', 'en'): ['d-txt-data-preprocessing-en', 'd-exl-data-preprocessing-en', 'd-img-data-preprocessing-en', 'd-abt-data-preprocessing-en'],
    ('ams:isTemporalMeasurementData', str): ['d-txt-temporal-measurement-data', 'd-exl-temporal-measurement-data', 'd-img-temporal-measurement-data', 'd-abt-temporal-measurement-data'],
    ('ams:numberOfRows', int): ['d-txt-number-of-rows', 'd-exl-number-of-rows', 'd-abt-number-of-rows'],
    ('ams:numberOfColumns', int): ['d-txt-number-of-columns', 'd-exl-number-of-columns', 'd-abt-number-of-columns'],
    ('ams:approximateNumberOfSimilarFiles', str): ['d-txt-approximate-number-of-similar-files', 'd-exl-approximate-number-of-similar-files', 'd-img-approximate-number-of-similar-files', 'd-abt-approximate-number-of-similar-files'],
    ('ams:delimiter', str): ['t-txt-delimiter', 't-abt-delimiter'],
    ('ams:characterCode', str): ['t-txt-character-code', 't-abt-character-code'],
    ('ams:remarks', 'ja'): ['t-txt-remarks-jp', 't-exl-remarks-jp', 't-img-remarks-jp', 't-abt-remarks-jp'],
    ('ams:remarks', 'en'): ['t-txt-remarks-en', 't-exl-remarks-en', 't-img-remarks-en', 't-abt-remarks-en'],
    ('ams:widthPixels', int): ['d-img-pixel-width', 'd-abt-pixel-width'],
    ('ams:heightPixels', int): ['d-img-pixel-height', 'd-abt-pixel-height'],
    ('ams:resolutionHorizontal', str): ['d-img-resolution-horizontal', 'd-abt-resolution-horizontal'],
    ('ams:resolutionVertical', str): ['d-img-resolution-vertical', 'd-abt-resolution-vertical'],
    ('ams:numberOfColorInformation', str): ['t-img-Color-Monochrome', 't-abt-Color-Monochrome'],
    ('ams:colorBits', str): ['t-img-number-of-color-bit', 't-abt-number-of-color-bit'],
    ('ams:compressedFormat', str): ['t-img-compression-format', 't-abt-compression-format'],
    ('ams:imageType', str): ['t-img-image-type', 't-abt-image-type'],
    ('ams:fileType', str): ['t-abt-text/binary'],
    ('ams:structureInformation', 'rdm:MetadataDocument'): ['grdm-file:d-txt-file-name-convention-file-extension', 'grdm-file:d-exl-file-name-convention-file-extension', 'grdm-file:d-img-file-name-convention-file-extension', 'grdm-file:d-abt-file-name-convention-file-extension'],
    ('ams:storageFolder', str): ['storage-folder'],
}
