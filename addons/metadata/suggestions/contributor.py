import logging
from datetime import date
from framework.auth.core import _get_current_user
from .utils import (
    to_msfullname,
    contributors_self_first,
    build_display_fullname,
)


logger = logging.getLogger(__name__)


def _contributor_to_name_ja_full(user):
    return '|'.join([
        part for part in [
            user.family_name_ja,
            user.middle_names_ja,
            user.given_name_ja,
        ]
        if len(part) > 0
    ])


def _contributor_to_name_en_full(user):
    return '|'.join([
        part for part in [
            user.family_name,
            user.middle_names,
            user.given_name,
        ]
        if len(part) > 0
    ])


def suggestion_contributor(key, keyword, node):
    contributors = []
    current_user = _get_current_user()
    ordered_users = contributors_self_first(node, current_user=current_user)
    for user in ordered_users:
        # Use affiliated institutions only
        org_ja = ''
        org_en = ''
        inst = user.affiliated_institutions.first()
        if inst is not None and inst.name:
            org_ja = inst.name

        # Current year as nendo for contributor suggestions
        nendo = str(date.today().year)

        name_ja_full = _contributor_to_name_ja_full(user)
        name_en_full = _contributor_to_name_en_full(user)
        name_ja_struct = _contributor_to_name_ja(user)
        name_en_struct = _contributor_to_name_en(user)
        display_fullname = build_display_fullname(name_ja_struct, name_en_struct)
        contributors.append({
            'erad': user.erad or '',
            'name': f'{name_ja_full}/{name_en_full}',
            'name-ja-full': name_ja_full,
            'name-en-full': name_en_full,
            'display-fullname': display_fullname,
            'name-ja': name_ja_struct,
            'name-en': name_en_struct,
            'name-ja-msfullname': to_msfullname(name_ja_struct, 'ja'),
            'name-en-msfullname': to_msfullname(name_en_struct, 'en'),
            'nendo': nendo,
            'affiliated-institution-name-ja': org_ja,
            'affiliated-institution-name-en': org_en,
            'affiliated-institution-name': f'{org_ja}/{org_en}',
        })
    search_key = key.split(':')[1]
    if search_key == 'erad':
        contributors = [
            cont for cont in contributors
            if keyword.lower() in cont['erad'].lower()
        ]
    elif search_key == 'name':
        logger.debug('Filtering contributors by name keyword: %s', keyword)
        for c in contributors:
            logger.debug('Contributor: erad=%s, name-ja-full=%s, name-en-full=%s',
                         c['erad'], c['name-ja-full'], c['name-en-full'])
        contributors = [
            cont for cont in contributors
            if any([
                keyword.lower() in cont['name-ja-full'].lower(),
                keyword.lower() in cont['name-en-full'].lower(),
            ])
        ]
    elif search_key == 'affiliated-institution-name':
        contributors = [
            cont for cont in contributors
            if any([
                keyword.lower() in (cont.get('affiliated-institution-name-ja') or '').lower(),
                keyword.lower() in (cont.get('affiliated-institution-name-en') or '').lower(),
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


def _contributor_to_name_ja(user):
    return {
        'last': user.family_name_ja,
        'middle': user.middle_names_ja,
        'first': user.given_name_ja,
    }


def _contributor_to_name_en(user):
    return {
        'last': user.family_name,
        'middle': user.middle_names,
        'first': user.given_name,
    }
