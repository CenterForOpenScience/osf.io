
import os
from mako.lookup import TemplateLookup

CLASS_MAP = {
    'full': 'success',
    'partial': 'warning',
    'none': 'danger',
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
            if status.strip(' ') == 'NA':
                continue
            split = status.split(' | ')
            infos.append({
                'function': cap,
                'status': split[0],
                'detail': split[1] if len(split) > 1 else '',
                'class': CLASS_MAP[split[0]],
            })
        terms = [
            line[col]
            for line in lines[row + 1:]
            if len(line) > col
        ]
        rv[addon] = {
            'capabilities': infos,
            'terms': terms,
        }

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
