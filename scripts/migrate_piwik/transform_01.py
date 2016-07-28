import re
import sys
import json
import uuid
import sqlite3
from datetime import datetime, timedelta
from hashlib import sha256, md5

from geoip import geolite2

from modularodm import Q

from website.app import init_app
from website.models import User, Node, NodeLog
from website.util.metrics import get_entry_point

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings
from scripts.migrate_piwik import lookup_data


def main(force=False):

    history_run_id = utils.get_history_run_id_for('extract')
    complaints_run_id = utils.get_complaints_run_id_for('extract')
    if history_run_id != complaints_run_id:
        print("You need to validate your exported data! Bailing...")
        sys.exit()

    extract_complaints = utils.get_complaints_for('extract', 'r')
    extract_complaints.readline()  # toss header
    if extract_complaints.readline():
        print("You have unaddressed complaints!")
        if not force:
            print("  ...pass --force to ignore")
            sys.exit()

    sqlite_db = sqlite3.connect(settings.SQLITE_PATH)
    sqlite_setup(sqlite_db)

    input_file = open(utils.get_dir_for('extract') + '/' + settings.EXTRACT_FILE, 'r')
    transform_dir = utils.get_dir_for('transform01')
    output_file = open(transform_dir + '/' + settings.TRANSFORM01_FILE, 'w')

    history_file = utils.get_history_for('transform01', 'w')
    history_file.write('Run ID: {}\n'.format(complaints_run_id))
    history_file.write('Beginning extraction at: {}Z\n'.format(datetime.utcnow()))

    user_cache = {}
    node_cache = {}
    location_cache = {}

    linenum = 0
    tally = {'missing_user': 0, 'missing_node': 0}
    for pageview_json in input_file.readlines():
        linenum += 1
        if not linenum % 1000:
            print('Transforming line {}'.format(linenum))

        raw_pageview = json.loads(pageview_json)
        visit = raw_pageview['visit']
        action = raw_pageview['action']

        # lookup location by ip address. piwik strips last 16 bits, so may not be completely
        # accurate, but should be close enough.
        location = None
        ip_addr = visit['ip_addr']
        if ip_addr is not None:
            if not location_cache.has_key(ip_addr):
                location_cache[ip_addr] = geolite2.lookup(ip_addr)
            location = location_cache[ip_addr]

        # user has many visitor ids, visitor id has many session ids.
        # in keen, visitor id will refresh 1/per year, session 1/per 30min.
        visitor_id = get_or_create_visitor_id(visit['visitor_id'], sqlite_db)
        session_id = get_or_create_session_id(visit['id'], sqlite_db)

        user_entry_point = None
        user_locale = None
        user_timezone = None
        user_institutions = None

        user_id = visit['user_id']
        if user_id is not None:
            if not user_cache.has_key(user_id):
                user_obj = User.load(user_id)
                user_cache[user_id] = {
                    'entry_point': None if user_obj is None else get_entry_point(user_obj),
                    'locale': user_obj.locale if user_obj else '',
                    'timezone': user_obj.timezone if user_obj else '',
                    'institutions': [
                        {'id': inst._id, 'name': inst.name, 'logo_path': inst.logo_path}
                        for inst in user_obj.affiliated_institutions
                    ] if user_obj else [],
                }

            user_entry_point = user_cache[user_id]['entry_point']
            user_locale = user_cache[user_id]['locale']
            user_timezone = user_cache[user_id]['timezone']
            user_institutions = user_cache[user_id]['institutions']


        node = None
        node_id = action['node_id']
        if node_id is not None:
            if not node_cache.has_key(node_id):
                node_cache[node_id] = Node.load(node_id)
            node = node_cache[node_id]


        node_public_date = None
        if node is not None:
            privacy_actions = NodeLog.find(
                Q('node', 'eq', node_id)
                & Q('action', 'in', [NodeLog.MADE_PUBLIC, NodeLog.MADE_PRIVATE])
            ).sort('-date')

            try:
                privacy_action = privacy_actions[0]
            except IndexError as e:
                pass
            else:
                if privacy_action.action == NodeLog.MADE_PUBLIC:
                    node_public_date = privacy_action.date.isoformat()
                    node_public_date = node_public_date[:-3] + 'Z'

        browser_version = [None, None]
        if visit['ua']['browser']['version']:
            browser_version = visit['ua']['browser']['version'].split('.')

        os_version = [None, None]
        if visit['ua']['os_version']:
            os_version = visit['ua']['os_version'].split('.')
            if len(os_version) == 1:
                os_version.append(None)

        os_family = parse_os_family(visit['ua']['os']);
        if visit['ua']['os'] == 'WIN' and visit['ua']['os_version']:
            os_family = os_family.replace('<Unknown Version>', visit['ua']['os_version'])

        browser_info = {
            'device': {
                'family': visit['ua']['device'],
            },
            'os': {
                'major': os_version[0],
                'patch_minor': None,
                'minor': os_version[1],
                'family': os_family,
                'patch': None,
            },
            'browser': {
                'major': browser_version[0],
                'minor': browser_version[1],
                'family': parse_browser_family(visit['ua']['browser']['name']),
                'patch': None,
            },
        }

        if '-' in visit['ua']['browser']['locale']:
            browser_locale = visit['ua']['browser']['locale'].split('-')
            browser_language = '-'.join([browser_locale[0], browser_locale[1].upper()])

        node_tags = None if action['node_tags'] is None else [
            tag for tag in action['node_tags'].split(',')
        ]

        # piwik stores resolution as 1900x600 mostly, but sometimes as a float?
        # For the sake of my sanity and yours, let's ignore floats.
        screen_resolution = (None, None)
        if re.search('x', visit['ua']['screen']):
            screen_resolution = visit['ua']['screen'].split('x')

        # piwik fmt: '2016-05-11 20:30:00', keen fmt: '2016-06-30T17:12:50.070Z'
        # piwik is always utc
        utc_timestamp = datetime.strptime(action['timestamp'], '%Y-%m-%d %H:%M:%S')
        utc_ts_formatted = utc_timestamp.isoformat() + '.000Z'  # naive, but correct

        local_timedelta = timedelta(minutes=visit['tz_offset'])
        local_timestamp = utc_timestamp + local_timedelta

        pageview = {
            'meta': {
                'epoch': 0,  # migrated from piwik
            },
            'page': {
                'title': action['page']['title'],
                'url': action['page']['url_prefix'] + action['page']['url'] if action['page']['url'] is not None else None,
                'info': {}  # (add-on)
            },
            'referrer': {
                'url': action['referrer'] or None,
                'info': {}, # (add-on)
            },
            'tech': {
                'browser': {  # JS-side will be filled in by Keen.helpers.getBrowserProfile()
                    'cookies': True if visit['ua']['browser']['cookies'] else False,
                    'language': browser_language,
                    'screen': {
                        'height': screen_resolution[1],
                        'width': screen_resolution[0],
                    },
                },
                'ip': ip_addr,  # private
                'ua': None,
                'info': browser_info,
            },
            'time': {
                'utc': timestamp_components(utc_timestamp),
                'local':  timestamp_components(local_timestamp),
            },
            'visitor': {
                'id': visitor_id,
                'session': session_id,
                'returning': True if visit['visitor_returning'] else False,  # visit
            },
            'user': {
                'id': user_id,
                'entry_point': user_entry_point or '',  # empty string if no user
                'locale': user_locale or '',  # empty string if no user
                'timezone': user_timezone or '',  # empty string if no user
                'institutions': user_institutions,  # null if no user, else []
            },
            'node': {
                'id': node_id,
                'title': getattr(node, 'title', None),
                'type': getattr(node, 'category', None),
                'tags': node_tags,
                'made_public_date': node_public_date,
            },
            'geo': {},
            'anon': {
                'id': md5(session_id).hexdigest(),
                'continent': getattr(location, 'continent', None),
                'country': getattr(location, 'country', None),
            },
            'keen': {
                'timestamp': utc_ts_formatted,
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
                    },
                    {  # private
                        'name': 'keen:ip_to_geo',
                        'input': {
                            'ip': 'tech.ip'
                        },
                        'output': 'geo',
                    }
                ],
            }
        }

        if node_id is None:
            tally['missing_node'] += 1

        if user_id is None:
            tally['missing_user'] += 1

        output_file.write(json.dumps(pageview) + '\n')

    history_file.write('Finished extraction at: {}Z\n'.format(datetime.utcnow()))
    history_file.write('Final count was: {}\n'.format(linenum))
    history_file.write('{} pageviews lacked a user id.\n'.format(tally['missing_user']))
    history_file.write('{} pageviews lacked a node id.\n'.format(tally['missing_node']))
    sqlite_db.close()


def sqlite_setup(sqlite_db):
    """Test whether we already have an sqlite db for mapping Piwik visitor ids to keen visitor ids,
    and Piwik visit ids to session ids. If not, create them.
    :return:
    """
    cursor = sqlite_db.cursor()

    try:
        cursor.execute('SELECT COUNT(*) FROM visitor_ids')
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE visitor_ids (piwik_id TEXT, keen_id TEXT)')
        sqlite_db.commit()

    try:
        cursor.execute('SELECT COUNT(*) FROM session_ids')
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE session_ids (visit_id TEXT, session_id TEXT)')
        sqlite_db.commit()


def get_or_create_visitor_id(piwik_id, sqlite_db):
    """Gets or creates a new Keen visitor UUID given a Piwik visitor ID.

    :param piwik_id: Piwik visitor ID from current row in database
    :param sqlite_db: SQLite3 database handle
    :return: Keen visitor UUID as str
    """
    cursor = sqlite_db.cursor()
    query = "SELECT * FROM visitor_ids WHERE piwik_id='{p_id}'".format(p_id=piwik_id)
    cursor.execute(query)

    keen_ids = cursor.fetchall()

    if len(keen_ids) > 1:
        raise Exception("Multiple ID's found for single Piwik User ID")

    if keen_ids:
        return str(keen_ids[0][1])

    keen_id = str(uuid.uuid4())
    query = "INSERT INTO visitor_ids (piwik_id, keen_id) VALUES ('{p_id}', '{k_id}');".format(
        p_id=piwik_id, k_id=keen_id
    )
    cursor.execute(query)
    sqlite_db.commit()
    return keen_id


def get_or_create_session_id(visit_id, sqlite_db):
    """Gets or creates a new session UUID given a Piwik visit ID.

    :param user_id: Piwik visit ID from current row in database
    :param sqlite_db: SQLite3 database handle
    :return: session UUID as str
    """
    cursor = sqlite_db.cursor()
    query = "SELECT * FROM session_ids WHERE visit_id='{p_id}'".format(p_id=str(visit_id))
    cursor.execute(query)

    session_ids = cursor.fetchall()

    if len(session_ids) > 1:
        raise Exception("Multiple session ID\'s found for single Piwik visit ID")

    if session_ids:
        return str(session_ids[0][1])

    session_uuid = str(uuid.uuid4())
    query = "INSERT INTO session_ids (visit_id, session_id) VALUES ('{visit}', '{session}');".format(
        visit=str(visit_id), session=session_uuid
    )
    cursor.execute(query)
    sqlite_db.commit()
    return session_uuid


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


def timestamp_components(timestamp):
    return {
        'hour_of_day': timestamp.hour,
        'day_of_week': timestamp.isoweekday(),
        'day_of_month': timestamp.day,
        'month': timestamp.month,
        'year': timestamp.year,
    }

if __name__ == "__main__":
    init_app(set_backends=True, routes=False)
    force = '--force' in sys.argv
    main(force=force)
