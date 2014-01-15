
import os
from mako.lookup import TemplateLookup

CLASS_MAP = {
    'Supported': 'success',
    'Partially supported': 'warning',
    'Not supported': 'danger',
}

def read_capabilities(filename):

    lines = open(filename).readlines()
    lines = [
        line.rstrip().split('\t')
        for line in lines
    ]

    addons = [
        (col, cell.strip())
        for col, cell in enumerate(lines[1])
        if cell
    ]
    caps = [
        (row, line[0].strip())
        for row, line in enumerate(lines)
        if line[0].strip()
    ]

    rv = {}

    for col, addon in addons:
        infos = []
        for row, cap in caps:
            status = lines[row][col]
            try:
                message = lines[row][col+1]
            except IndexError:
                message = ''
            infos.append({
                'function': cap,
                'status': status,
                'detail': message,
                'class': CLASS_MAP[status],
            })
        rv[addon] = infos

    return rv

here, _ = os.path.split(__file__)
here = os.path.abspath(here)

lookup = TemplateLookup(
    directories=[os.path.join(here, 'templates')]
)
template = lookup.get_template('capabilities.mako')

CAPABILITIES = read_capabilities(os.path.join(here, 'data', 'addons.tsv'))

def render_addon_capabilities(addons_available):

    rendered = {}

    for addon_config in addons_available:
        if addon_config.full_name in CAPABILITIES:
            rendered[addon_config.short_name] = template.render(
                full_name=addon_config.full_name,
                **{'caps': CAPABILITIES[addon_config.full_name]}
            )

    return rendered