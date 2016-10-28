import logging
import argparse
import importlib
from datetime import datetime

from keen.client import KeenClient

from website.app import init_app
from website.settings import KEEN as keen_settings
from scripts.analytics.addon_snapshot import get_events as addon_events

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def gather_snapshot_events(scripts=None):
    today = datetime.datetime.utcnow().date()
    logger.info('<---- Gatheirng snapshot data for right now: {} ---->'.format(today.isoformat()))

    keen_events = {}
    if scripts:
        for script in scripts:
            try:
                script_events = importlib.import_module('scripts.analytics.{}'.format(script))
                keen_events.update({script: script_events.get_events()})
            except ImportError as e:
                logger.error(e)
                logger.error('Error importing script - make sure the script specified is inside of scripts/analytics')

    keen_events.update({'addon_snapshot': addon_events()})

    return keen_events


def parse_args():
    parser = argparse.ArgumentParser(description='Populate keen counts!')
    parser.add_argument(
        '-as', '--analytics_scripts', nargs='+', dest='analytics_scripts', required=False,
        help='Enter the names of scripts inside scripts/analytics you would like to run separated by spaces (ex: -as user_summary node_summary)'
    )
    return parser.parse_args()


def main(scripts=None):
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

    keen_events = gather_snapshot_events(scripts=None)
    client.add_events(keen_events)


if __name__ == '__main__':
    init_app()
    main()
