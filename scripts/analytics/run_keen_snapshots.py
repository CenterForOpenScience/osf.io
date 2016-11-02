import logging
import argparse
import importlib

from scripts.analytics.addon_snapshot import AddonSnapshot

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(description='Populate keen counts!')
    parser.add_argument(
        '-as', '--analytics_scripts', nargs='+', dest='analytics_scripts', required=False,
        help='Enter the names of scripts inside scripts/analytics you would like to run separated by spaces (ex: -as user_summary node_summary)'
    )
    return parser.parse_args()


def main(me_scripts):
    """ Gathers a snapshot of analytics at the time the script was run,
    and only for that time. Cannot be back-dated.
    """
    args = parse_args()
    me_scripts = args.analytics_scripts
    snapshot_classes = []
    if me_scripts:
        for one_script in me_scripts:
            try:
                import scripts
                script_class_name = ''.join([item.capitalize() for item in one_script.split('_')])
                script_events = importlib.import_module('scripts.analytics.{}'.format(one_script))
                script_class = eval('{}.{}'.format(script_events.__name__, script_class_name))
                snapshot_classes.append(script_class)
            except ImportError as e:
                logger.error(e)
                logger.error(
                    'Error importing script - make sure the script specified is inside of scripts/analytics. '
                    'Also make sure the main analytics class name is the same as the script name but in camel case. '
                    'For example, the script named  scripts/analytics/addon_snapshot.py has class AddonSnapshot'
                )
    else:
        snapshot_classes = [AddonSnapshot]

    for analytics_class in snapshot_classes:
        class_instance = analytics_class()
        events = class_instance.get_events()
        class_instance.send_events(events)


if __name__ == '__main__':
    args = parse_args()
    the_scripts = args.analytics_scripts

    main(the_scripts)
