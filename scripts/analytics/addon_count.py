import sys
from datetime import date
from dateutil.parser import parse

from website.settings import ADDONS_AVAILABLE
from website.app import init_app
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

def count(today):
    counts = []
    for addon in ADDONS_AVAILABLE:
        counts.append({
            'provider': addon.short_name,
            'user_count': addon.settings_models['user'].find().count() if addon.settings_models.get('user') else 0,
            'node_count': addon.settings_models['node'].find().count() if addon.settings_models.get('node') else 0
        })
    return {'addon_count_analytics': counts}

def main(today):
    keen_payload = count(today)
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_events(keen_payload)
    else:
        print(keen_payload)


if __name__ == '__main__':
    init_app()
    try:
        date = parse(sys.argv[1])
    except IndexError:
        date = date.today()
    main(date)
