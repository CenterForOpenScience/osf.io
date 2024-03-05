import logging

import requests
from rest_framework import status as http_status

from framework.exceptions import HTTPError
from osf.models import BaseFileNode
from osf.models.files import UnableToResolveFileClass
from osf.utils.fields import EncryptedTextField, EncryptedJSONField
from . import SHORT_NAME
from .models import ERadRecord

logger = logging.getLogger(__name__)


ERAD_COLUMNS = [
    'KENKYUSHA_NO', 'KENKYUSHA_SHIMEI', 'KENKYUKIKAN_CD', 'KENKYUKIKAN_MEI',
    'HAIBUNKIKAN_CD', 'HAIBUNKIKAN_MEI', 'NENDO', 'SEIDO_CD', 'SEIDO_MEI',
    'JIGYO_CD', 'JIGYO_MEI', 'KADAI_ID', 'KADAI_MEI', 'BUNYA_CD', 'BUNYA_MEI',
    'JAPAN_GRANT_NUMBER', 'PROGRAM_NAME_JA', 'PROGRAM_NAME_EN', 'FUNDING_STREAM_CODE',
]

ROR_URL = 'https://api.ror.org/organizations'


def valid_suggestion_key(key):
    if key == 'file-data-number':
        return True
    elif key == 'ror':
        return True
    elif key.startswith('erad:'):
        return True
    elif key.startswith('asset:'):
        return True
    elif key.startswith('contributor:'):
        return True
    return False


def suggestion_metadata(key, keyword, filepath, node):
    suggestions = []
    if key == 'file-data-number':
        suggestions.extend(suggestion_file_data_number(key, filepath, node))
    elif key == 'ror':
        suggestions.extend(suggestion_ror(key, keyword))
    elif key.startswith('erad:'):
        suggestions.extend(suggestion_erad(key, keyword, node))
    elif key.startswith('asset:'):
        suggestions.extend(suggestion_asset(key, keyword, node))
    elif key.startswith('contributor:'):
        suggestions.extend(suggestion_contributor(key, keyword, node))
    else:
        raise KeyError('Invalid key: {}'.format(key))
    return suggestions


def suggestion_file_data_number(key, filepath, node):
    parts = filepath.split('/')
    is_dir = parts[0] == 'dir'
    if is_dir:
        value = 'files/{}'.format(filepath)
    else:
        provider = parts[0]
        path = '/'.join(parts[1:])
        try:
            file_node = BaseFileNode.resolve_class(provider, BaseFileNode.FILE).get_or_create(node, path)
        except UnableToResolveFileClass:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)
        guid = file_node.get_guid(create=True)
        guid.referent.save()
        value = guid._id
    return [{
        'key': key,
        'value': value,
    }]


def suggestion_ror(key, keyword):
    response = requests.get(
        ROR_URL,
        params={
            'query': keyword,
        }
    )
    response.raise_for_status()
    res = []
    for item in response.json()['items']:
        labels = item.get('labels', [])
        name_ja = next((l['label'] for l in labels if l['iso639'] == 'ja'), item['name'])
        res.append({
            'key': key,
            'value': {
                **item,
                'name-ja': name_ja,
            }
        })
    return res


def suggestion_erad(key, keyword, node):
    filter_field_name = key[5:]
    filter_field = ERadRecord._meta.get_field(filter_field_name)
    if isinstance(filter_field, EncryptedTextField) or isinstance(filter_field, EncryptedJSONField):
        # cannot filter by encrypted field
        candidates = [
            r
            for r in _erad_candidates_for_node(node)
            if keyword.lower() in r[filter_field_name].lower()
        ]
    else:
        candidates = _erad_candidates_for_node(node, **{f'{filter_field_name}__icontains': keyword})
    res = []
    for candidate in candidates:
        names = candidate.get('kenkyusha_shimei', '').split('|')
        ja_parts = names[:len(names) // 2]
        en_parts = names[len(names) // 2:]
        kikan_parts = candidate.get('kenkyukikan_mei', '').split('|')
        kikan_ja = kikan_parts[0]
        kikan_en = kikan_parts[1] if len(kikan_parts) > 1 else ''
        res.append({
            'key': key,
            'value': {
                **candidate,
                'kenkyusha_shimei_ja': {
                    'last': ja_parts[0],
                    'middle': ''.join(ja_parts[1:-1]),
                    'first': ja_parts[-1],
                },
                'kenkyusha_shimei_en': {
                    'last': en_parts[0] if len(en_parts) > 0 else '',
                    'middle': ''.join(en_parts[1:-1]),
                    'first': en_parts[-1] if len(en_parts) > 0 else '',
                },
                'kenkyukikan_mei_ja': kikan_ja,
                'kenkyukikan_mei_en': kikan_en,
            },
        })
    return res


def _erad_candidates_for_node(node, **pred):
    return sum([  # flatten
        _erad_candidates(**{**pred, 'kenkyusha_no': user.erad})
        for user in node.contributors
        if user.erad is not None
    ], [])


def _erad_candidates(**pred):
    return [
        dict([
            (k.lower(), getattr(record, k.lower()))
            for k in ERAD_COLUMNS
        ])
        for record in ERadRecord.objects.filter(**pred)
    ]


def suggestion_asset(key, keyword, node):
    addon = node.get_addon(SHORT_NAME)
    assets = addon.get_metadata_assets()
    res = []
    for asset in assets:
        key_target = asset.get(key[6:], '').lower()
        if len(key_target) > 0 and keyword in key_target:
            res.append({
                'key': key,
                'value': asset,
            })
    return res


def suggestion_contributor(key, keyword, node):
    contributors = [
        {
            'erad': user.erad,
            'name-ja-full': '|'.join([
                part for part in [
                    user.family_name_ja,
                    user.middle_names_ja,
                    user.given_name_ja,
                ]
                if len(part) > 0
            ]),
            'name-en-full': '|'.join([
                part for part in [
                    user.family_name,
                    user.middle_names,
                    user.given_name,
                ]
                if len(part) > 0
            ]),
            'name-ja': {
                'last': user.family_name_ja,
                'middle': user.middle_names_ja,
                'first': user.given_name_ja,
            },
            'name-en': {
                'last': user.family_name,
                'middle': user.middle_names,
                'first': user.given_name,
            },
        }
        for user in node.contributors
    ]
    search_key = key.split(':')[1]
    if search_key == 'erad':
        contributors = [
            cont for cont in contributors
            if keyword in cont['erad']
        ]
    elif search_key == 'name':
        contributors = [
            cont for cont in contributors
            if any([
                keyword in cont['name-ja-full'],
                keyword in cont['name-en-full'],
            ])
        ]
    else:
        raise KeyError('Invalid key: {}'.format(key))
    return [
        {
            'key': key,
            'value': cont
        }
        for cont in contributors
    ]
