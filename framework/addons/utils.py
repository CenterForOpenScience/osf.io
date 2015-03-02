import os
from json import loads as load_json
from mako.lookup import TemplateLookup

CLASS_MAP = {
    'full': 'success',
    'partial': 'warning',
    'none': 'danger',
}

CAPABILITY_SET = [
    'Permissions',
    'View / download file versions',
    'Add / update files',
    'Delete files',
    'Logs',
    'Forking',
    'Registering'
]

def read_capabilities(filename):

    data_file = open(filename, 'r')
    data = load_json(data_file.read())

    addons = data['addons']
    disclaimers = data['disclaimers']

    rv = {}

    for addon_name, info in addons.iteritems():
        infos = []
        for cap in CAPABILITY_SET:
            text = info[cap]
            if text == 'NA':
                continue
            split = text.split(' | ')
            infos.append({
                'function': cap,
                'status': split[0],
                'detail': split[1] if len(split) > 1 else '',
                'class': CLASS_MAP[split[0]],
            })
        rv[addon_name] = {
            'capabilities': infos,
            'terms': disclaimers,
        }

    return rv

here, _ = os.path.split(__file__)
here = os.path.abspath(here)

lookup = TemplateLookup(
    directories=[os.path.join(here, 'templates')]
)
template = lookup.get_template('capabilities.mako')

CAPABILITIES = read_capabilities(os.path.join(here, 'data', 'addons.json'))

def render_addon_capabilities(addons_available):

    rendered = {}

    for addon_config in addons_available:
        if addon_config.full_name in CAPABILITIES:
            rendered[addon_config.short_name] = template.render(
                full_name=addon_config.full_name,
                **{'caps': CAPABILITIES[addon_config.full_name]}
            )

    return rendered
