from .utils import to_msfullname


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
            'name-ja': _contributor_to_name_ja(user),
            'name-en': _contributor_to_name_en(user),
            'name-ja-msfullname': to_msfullname(_contributor_to_name_ja(user), 'ja'),
            'name-en-msfullname': to_msfullname(_contributor_to_name_en(user), 'en'),
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
