import os
from json import load as load_json
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
    data = load_json(data_file)

    addons = data['addons']
    disclaimers = data['disclaimers']

    ret = {}

    for addon_name, info in addons.iteritems():
        infos = []
        for cap in CAPABILITY_SET:
            status = info[cap].get('status') or ''
            text = info[cap].get('text') or ''
            if status == 'NA':
                continue
            infos.append({
                'function': cap,
                'status': status,
                'detail': text,
                'class': CLASS_MAP[status],
            })
        ret[addon_name] = {
            'capabilities': infos,
            'terms': disclaimers,
        }

    data_file.close()
    return ret

here, _ = os.path.split(__file__)
here = os.path.abspath(here)

lookup = TemplateLookup(
    directories=[os.path.join(here, 'templates')],
    default_filters=[
        'unicode',  # default filter; must set explicitly when overriding
        'temp_ampersand_fixer',  # FIXME: Temporary workaround for data stored in wrong format in DB. Unescape it before it gets re-escaped by Markupsafe. See [#OSF-4432]
        'h',
    ],
    imports=[
        'from website.util.sanitize import temp_ampersand_fixer',  # FIXME: Temporary workaround for data stored in wrong format in DB. Unescape it before it gets re-escaped by Markupsafe. See [#OSF-4432]
    ]
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
