import sys
import json
import uuid
import sqlite3
from hashlib import sha256
from datetime import datetime

from geoip import geolite2

from website.app import init_app
import website.settings as settings
from website.models import User, Node
from website.util.metrics import get_entry_point

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import lookup_data
from scripts.migrate_piwik import settings as script_settings


def main():

    history_run_id = utils.get_history_run_id_for('extract')
    complaints_run_id = utils.get_complaints_run_id_for('extract')
    if history_run_id != complaints_run_id:
        print("You need to validate your exported data! Bailing...")
        sys.exit()

    extract_complaints = utils.get_complaints_for('extract', 'r')
    extract_complaints.readline()  # toss header
    if extract_complaints.readline():
        print("You have unaddressed complaints! Bailing...")
        sys.exit()

    sqlite_db = sqlite3.connect('piwik_users.sqlite')
    sqlite_setup(sqlite_db)

    input_file = open(utils.get_dir_for('extract') + '/' + script_settings.EXTRACT_FILE, 'r')
    transform_dir = utils.get_dir_for('transform01')
    output_file = open(transform_dir + '/' + script_settings.TRANSFORM01_FILE, 'w')

    history_file = utils.get_history_for('transform01', 'w')
    history_file.write('Run ID: {}\n'.format(complaints_run_id))
    history_file.write('Beginning extraction at: {}Z\n'.format(datetime.utcnow()))

    linenum = 0
    tally = {'missing_user': 0, 'missing_node': 0}
    for pageview_json in input_file.readlines():
        linenum += 1
        if not linenum % 1000:
            print('Transforming line {}'.format(linenum))

        raw_pageview = json.loads(pageview_json)
        visit = raw_pageview['visit']
        action = raw_pageview['action']

        location = None
        if visit['ip_addr'] is not None:
            location = geolite2.lookup(visit['ip_addr'])

        session_id = str(uuid.uuid4())
        keen_id = get_or_create_keen_id(visit['visitor_id'], sqlite_db)
        user = User.load(visit['user_id']) or None
        node = Node.load(action['node_id']) or None
        anon_id = None
        if visit['user_id']:
            anon_id = sha256(visit['user_id'] + settings.ANALYTICS_SALT).hexdigest()

        user_entry_point = get_entry_point(user) if user else None
        browser_info = {
            'device': {
                'family': None
            },
            'os': {
                'major': None,
                'patch_minor': None,
                'minor': None,
                'family': parse_os_family(visit['ua']['os']), #Needs parser
                'patch': None
            },
            'browser': {
                'major': None,
                'minor': None,
                'family': parse_browser_family(visit['ua']['browser']['name']),  # Needs parser
                'patch': None
            },
            'resolution': visit['ua']['screen'],
        }

        if visit['ua']['browser']['version']:
            browser_version = visit['ua']['browser']['version']
            browser_info['browser']['major'] = browser_version.split('.')[0]
            browser_info['browser']['minor'] = browser_version.split('.')[1]

        node_tags = action['node_tags'] or ''

        pageview = {
            'page': {
                'title': action['page']['title'],
                'url': action['page']['url_prefix'] + action['page']['url'],
                'info': {}  # (add-on)
            },
            'referrer': {
                'url': action['referrer'] or None,
                'info': {}, # (add-on)
            },
            'tech': {
                'browser': {},  # JS: Keen.helpers.getBrowserProfile(),
                'ip': None,
                'ua': None,  # manual
                'info': browser_info,
            },
            'time': {
                'utc': parse_server_time(action['timestamp']),
                'local': {}
            },
            'visitor': {
                'id': keen_id,
                'session': session_id,  # random val (sessionId)
                'returning': True if visit['visitor_returning'] else False,  # visit
            },
            'user': {
                'entryPoint': user_entry_point,
            },
            'node': {
                'id': action['node_id'],
                'title': getattr(node, 'title', None),
                'type': getattr(node, 'category', None),
                'tags': [tag for tag in node_tags.split(',')]
            },
            'geo': {},
            'anon': {
                'id': anon_id,
                'continent': getattr(location, 'continent', None),
                'country': getattr(location, 'country', None),
                'latitude': getattr(location, 'location', (None, None))[0],
                'longitude': getattr(location, 'location', (None, None))[1],
            },
            'keen': {
                'timestamp': action['timestamp'],
                'addons': [
                    {
                        'name': 'keen:referrer_parser',
                        'input': {
                            'referrer_url': 'referrer.url',
                            'page_url': 'page.url'
                        },
                        'output': 'referrer.info'
                    },
                    {
                        'name': 'keen:url_parser',
                        'input': {
                            'url': 'page.url'
                        },
                        'output': 'page.info'
                    },
                    {
                        'name': 'keen:url_parser',
                        'input': {
                            'url': 'referrer.url'
                        },
                        'output': 'referrer.info'
                    }
                ]
            }
        }

        pageview['user']['id'] = visit['user_id'] or None
        pageview['tech']['ip'] = visit['ip_addr']
        pageview['keen']['addons'].append({
            'name': 'keen:ip_to_geo',
            'input': {
                'ip': 'tech.ip'
            },
            'output': 'geo',
        })

        if action['node_id'] is None:
            tally['missing_node'] += 1

        if visit['user_id'] is None:
            tally['missing_user'] += 1

        output_file.write(json.dumps(pageview) + '\n')

    history_file.write('Finished extraction at: {}Z\n'.format(datetime.utcnow()))
    history_file.write('Final count was: {}\n'.format(linenum))
    history_file.write('{} pageviews lacked a user id.\n'.format(tally['missing_user']))
    history_file.write('{} pageviews lacked a node id.\n'.format(tally['missing_node']))
    sqlite_db.close()


def sqlite_setup(sqlite_db):
    """Test whether we already have an sqlite db for mapping Piwik user_ids to new keen ids,
    and if not create one. 
    :return:
    """
    cursor = sqlite_db.cursor()

    try:
        cursor.execute('SELECT COUNT(*) FROM matched_ids')
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE matched_ids (piwik_id TEXT, keen_id TEXT)')
        sqlite_db.commit()


def get_or_create_keen_id(user_id, sqlite_db):
    """Gets or creates a new Keen Id given a Piwik User Id from the db

    :param user_id: Piwik User Id from current row in database
    :param sqlite_db: SQLite3 database handle
    :return: Keen Id as str
    """
    cursor = sqlite_db.cursor()
    query = "SELECT * FROM matched_ids WHERE piwik_id='{p_id}'".format(p_id=user_id)
    cursor.execute(query)

    keen_id = cursor.fetchall()

    if len(keen_id) > 1:
        raise Exception("Multiple ID's found for single Piwik User ID")

    if not keen_id:
        keen_id = uuid.uuid4()
        query = "INSERT INTO matched_ids (piwik_id, keen_id) VALUES ('{p_id}', '{n_id}');".format(
            p_id=str(user_id), n_id=str(keen_id)
        )
        cursor.execute(query)
        sqlite_db.commit()
        return str(keen_id)

    return str(keen_id[0][1])


def parse_os_family(os_key):
    """Attempts to parse Piwik OS key codes into corresponding OS names

    :param os_name: Operating System keycode
    :return: Operating System name
    """

    if os_key in lookup_data.legacy_os_keys:
        os_key = lookup_data.legacy_os_keys[os_key]

    return lookup_data.os_keys.get(os_key, 'Unknown')


def parse_browser_family(browser_key):
    """Attempts to parse Piwik browser key codes into corresponding browser names

    :param browser_key: Browser keycode
    :return: Browser name
    """
    return lookup_data.browser_keys.get(browser_key, 'Unknown')


def parse_server_time(server_time):
    timestamp = datetime.strptime(server_time, '%Y-%m-%d %H:%M:%S')
    return {
        'hour_of_day': timestamp.hour,
        'day_of_week': timestamp.isoweekday(),
        'day_of_month': timestamp.day,
        'month': timestamp.month,
        'year': timestamp.year,
    }



if __name__ == "__main__":
    init_app(set_backends=True, routes=False)
    main()
