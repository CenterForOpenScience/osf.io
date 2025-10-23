from osf.utils.fields import EncryptedTextField, EncryptedJSONField
from ..models import ERadRecord
from .utils import contributors_self_first
from framework.auth.core import _get_current_user
from .utils import to_msfullname, build_display_fullname


ERAD_COLUMNS = [
    'KENKYUSHA_NO', 'KENKYUSHA_SHIMEI', 'KENKYUKIKAN_CD', 'KENKYUKIKAN_MEI',
    'HAIBUNKIKAN_CD', 'HAIBUNKIKAN_MEI', 'NENDO', 'SEIDO_CD', 'SEIDO_MEI',
    'JIGYO_CD', 'JIGYO_MEI', 'KADAI_ID', 'KADAI_MEI', 'BUNYA_CD', 'BUNYA_MEI',
    'JAPAN_GRANT_NUMBER', 'PROGRAM_NAME_JA', 'PROGRAM_NAME_EN', 'FUNDING_STREAM_CODE',
]


def suggestion_erad(key, keyword, node):
    # Detect current user for self-first ordering
    current_user = _get_current_user()
    filter_field_name = key[5:]
    filter_field = ERadRecord._meta.get_field(filter_field_name)
    if isinstance(filter_field, EncryptedTextField) or isinstance(filter_field, EncryptedJSONField):
        # cannot filter by encrypted field
        candidates = [
            r
            for r in _erad_candidates_for_node(node, current_user=current_user)
            if keyword.lower() in r[filter_field_name].lower()
        ]
    else:
        candidates = _erad_candidates_for_node(node, current_user=current_user, **{f'{filter_field_name}__icontains': keyword})
    res = []
    for candidate in candidates:
        names = candidate.get('kenkyusha_shimei', '').split('|')
        ja_parts = names[:len(names) // 2]
        en_parts = names[len(names) // 2:]
        kikan_parts = candidate.get('kenkyukikan_mei', '').split('|')
        kikan_ja = kikan_parts[0]
        kikan_en = kikan_parts[1] if len(kikan_parts) > 1 else ''
        kenkyusha_shimei_ja = {
            'last': ja_parts[0],
            'middle': ''.join(ja_parts[1:-1]),
            'first': ja_parts[-1],
        }
        kenkyusha_shimei_en = {
            'last': en_parts[0] if len(en_parts) > 0 else '',
            'middle': ''.join(en_parts[1:-1]),
            'first': en_parts[-1] if len(en_parts) > 0 else '',
        }
        res.append({
            'key': key,
            'value': {
                **candidate,
                'display_fullname': build_display_fullname(kenkyusha_shimei_ja, kenkyusha_shimei_en),
                'kenkyusha_shimei_ja': kenkyusha_shimei_ja,
                'kenkyusha_shimei_en': kenkyusha_shimei_en,
                'kenkyusha_shimei_ja_msfullname': to_msfullname(kenkyusha_shimei_ja, 'ja'),
                'kenkyusha_shimei_en_msfullname': to_msfullname(kenkyusha_shimei_en, 'en'),
                'kenkyukikan_mei_ja': kikan_ja,
                'kenkyukikan_mei_en': kikan_en,
            },
        })
    return res


def _erad_candidates_for_node(node, current_user=None, **pred):
    users = contributors_self_first(node, current_user=current_user)
    return sum([  # flatten preserving contributor order
        erad_candidates(**{**pred, 'kenkyusha_no': user.erad})
        for user in users
        if user.erad is not None
    ], [])


def erad_candidates(**pred):
    return [
        dict([
            (k.lower(), getattr(record, k.lower()))
            for k in ERAD_COLUMNS
        ])
        for record in ERadRecord.objects.filter(**pred)
    ]
