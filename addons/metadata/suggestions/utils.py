def to_msfullname(name, lang):
    names = []
    if 'last' not in name:
        raise ValueError('Invalid name: {}'.format(name))
    names.append(name['last'])
    if 'middle' in name:
        names.append(name['middle'])
    if 'first' not in name:
        raise ValueError('Invalid name: {}'.format(name))
    names.append(name['first'])
    names = [n.strip() for n in names]
    if lang == 'ja':
        return ''.join(names)
    names = [n for n in names if len(n) > 0]
    return ' '.join(names[::-1])
