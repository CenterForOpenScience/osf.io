import logging
from datetime import datetime

from keen.client import KeenClient

from website.app import init_app
from website.settings import KEEN as keen_settings
from scripts.analytics.addon_snapshot import get_events as addon_events

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



def gather_snapshot_events():
    today = datetime.datetime.utcnow().date()
    logger.info('<---- Gatheirng snapshot data for right now: {} ---->'.format(today.isoformat()))

    keen_events = {}
    keen_events.update({'addon_analytics': addon_events()})

    return keen_events


def main():
    """ Gathers a snapshot of analytics at the time the script was run,
    and only for that time. Cannot be back-dated.
    """
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
    assert(client)

    keen_events = gather_snapshot_events()
    client.add_events(keen_events)


if __name__ == '__main__':
    init_app()
    main()
