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
from scripts import utils as scripts_utils


import logging

logger = logging.getLogger(__name__)

def main(force=False):
    history_run_id = utils.get_history_run_id_for('extract')
    complaints_run_id = utils.get_complaints_run_id_for('extract')
    if history_run_id != complaints_run_id:
        print('You need to validate your exported data! Bailing...')
        sys.exit()

    extract_complaints = utils.get_complaints_for('extract', 'r')
    extract_complaints.readline()  # toss header
    if extract_complaints.readline():
        print('You have unaddressed complaints!')
        if not force:
            print('  ...pass --force to ignore')
            sys.exit()
    extract_complaints.close()

    sqlite_db = sqlite3.connect(settings.SQLITE_PATH)
    sqlite_db.row_factory = sqlite3.Row
    sqlite_setup(sqlite_db)

    transform_dir = utils.get_dir_for('transform01')

    logger.info('Run ID: {}\n'.format(complaints_run_id))
    logger.info('Beginning extraction at: {}Z\n'.format(datetime.utcnow()))
    tally = {'missing_user': 0, 'missing_node': 0}
    lastline = 0
    try:
        with open(utils.get_dir_for('transform01') + '/resume.log', 'r') as fp:
            fp.seek(-32, 2)
            lastline = int(fp.readlines()[-1].strip('\n'))
    except IOError:
        pass

    with open(utils.get_dir_for('transform01') + '/resume.log', 'a', 0) as resume_file:  # Pass 0 for unbuffered writing
        with open(transform_dir + '/' + settings.TRANSFORM01_FILE, 'a') as output_file:
            with open(utils.get_dir_for('extract') + '/' + settings.EXTRACT_FILE, 'r') as input_file:
                print('Lastline is: {}\n'.format(lastline))
                for i, pageview_json in enumerate(input_file):
                    linenum = i + 1
                    if linenum <= lastline:
                        if not linenum % 1000:
                            print('Skipping line {} of ***{}***'.format(linenum, lastline))
                        continue

                    if not linenum % 1000:
                        print('Transforming line {}'.format(linenum))

                    raw_pageview = json.loads(pageview_json)
                    visit = raw_pageview['visit']
                    action = raw_pageview['action']

                    # lookup location by ip address. piwik strips last 16 bits, so may not be completely
                    # accurate, but should be close enough.
                    ip_addr = visit['ip_addr']
                    location = get_location_for_ip_addr(ip_addr, sqlite_db)

                    # user has many visitor ids, visitor id has many session ids.
                    # in keen, visitor id will refresh 1/per year, session 1/per 30min.
                    visitor_id = get_or_create_visitor_id(visit['visitor_id'], sqlite_db)
                    session_id = get_or_create_session_id(visit['id'], sqlite_db)

                    user_id = visit['user_id']
                    user = get_or_create_user(user_id, sqlite_db)

                    node_id = action['node_id']
                    node = get_or_create_node(node_id, sqlite_db)

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
                            'info': {},  # (add-on)
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
                            'local': timestamp_components(local_timestamp),
                        },
                        'visitor': {
                            'id': visitor_id,
                            'session': session_id,
                            'returning': True if visit['visitor_returning'] else False,  # visit
                        },
                        'user': {
                            'id': user_id,
                            'entry_point': '' if user is None else user['entry_point'],  # empty string if no user
                            'locale': '' if user is None else user['locale'],  # empty string if no user
                            'timezone': '' if user is None else user['timezone'],  # empty string if no user
                            'institutions': None if user is None else user['institutions'],  # null if no user, else []
                        },
                        'node': {
                            'id': node_id,
                            'title': None if node is None else node['title'],
                            'type': None if node is None else node['category'],
                            'tags': node_tags,
                            'made_public_date': None if node is None else node['made_public_date'],
                        },
                        'geo': {},
                        'anon': {
                            'id': md5(session_id).hexdigest(),
                            'continent': None if location is None else location['continent'],
                            'country': None if location is None else location['country'],
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
                    resume_file.write(str(linenum) + '\n')

    logger.info('Finished extraction at: {}Z\n'.format(datetime.utcnow()))
    logger.info('Final count was: {}\n'.format(linenum))
    logger.info('{} pageviews lacked a user id.\n'.format(tally['missing_user']))
    logger.info('{} pageviews lacked a node id.\n'.format(tally['missing_node']))
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

    try:
        cursor.execute('SELECT COUNT(*) FROM nodes')
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE nodes (id TEXT, title TEXT, category TEXT, made_public_date TEXT)')
        sqlite_db.commit()

    try:
        cursor.execute('SELECT COUNT(*) FROM users')
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE users (id TEXT, entry_point TEXT, locale TEXT, timezone TEXT, institutions TEXT)')
        sqlite_db.commit()

    try:
        cursor.execute('SELECT COUNT(*) FROM locations')
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE locations (ip_addr TEXT, continent TEXT, country TEXT)')
        sqlite_db.commit()


def get_or_create_visitor_id(piwik_id, sqlite_db):
    """Gets or creates a new Keen visitor UUID given a Piwik visitor ID.

    :param piwik_id: Piwik visitor ID from current row in database
    :param sqlite_db: SQLite3 database handle
    :return: Keen visitor UUID as str
    """
    cursor = sqlite_db.cursor()
    query = "SELECT keen_id FROM visitor_ids WHERE piwik_id='{p_id}'".format(p_id=piwik_id)
    cursor.execute(query)

    keen_ids = cursor.fetchall()

    if len(keen_ids) > 1:
        raise Exception("Multiple ID's found for single Piwik User ID")

    if keen_ids:
        return str(keen_ids[0][0])

    keen_id = str(uuid.uuid4())
    query = "INSERT INTO visitor_ids (piwik_id, keen_id) VALUES ('{p_id}', '{k_id}');".format(
        p_id=piwik_id, k_id=keen_id
    )
    cursor.execute(query)
    sqlite_db.commit()
    return keen_id


def get_or_create_session_id(visit_id, sqlite_db):
    """Gets or creates a new session UUID given a Piwik visit ID.

    :param visit_id: Piwik visit ID from current row in database
    :param sqlite_db: SQLite3 database handle
    :return: session UUID as str
    """
    cursor = sqlite_db.cursor()
    query = "SELECT session_id FROM session_ids WHERE visit_id='{p_id}'".format(p_id=str(visit_id))
    cursor.execute(query)

    session_ids = cursor.fetchall()

    if len(session_ids) > 1:
        raise Exception("Multiple session ID\'s found for single Piwik visit ID")

    if session_ids:
        return str(session_ids[0][0])

    session_uuid = str(uuid.uuid4())
    query = "INSERT INTO session_ids (visit_id, session_id) VALUES ('{visit}', '{session}');".format(
        visit=str(visit_id), session=session_uuid
    )
    cursor.execute(query)
    sqlite_db.commit()
    return session_uuid

def get_location_for_ip_addr(ip_addr, sqlite_db):
    if ip_addr is None:
        return None

    cursor = sqlite_db.cursor()
    query = "SELECT * FROM locations WHERE ip_addr='{}'".format(ip_addr)
    cursor.execute(query)

    locations = cursor.fetchall()

    if len(locations) > 1:
        raise Exception('Multiple locations found for single ip address')

    if locations:
        return locations[0]

    location = geolite2.lookup(ip_addr)

    query = "INSERT INTO locations (ip_addr, continent, country) VALUES ('{ip_addr}', '{continent}', '{country}');".format(
        ip_addr=ip_addr,
        continent=getattr(location, 'continent', None),
        country=getattr(location, 'country', None),
    )
    cursor.execute(query)
    sqlite_db.commit()
    return get_location_for_ip_addr(ip_addr, sqlite_db)


def get_or_create_user(user_id, sqlite_db):
    """Gets an OSF user from the sqlite cache.  If not found, pulls the user info from mongo and
    saves it.

    :param user_id: OSF user id (e.g. 'mst3k')
    :param sqlite_db: SQLite3 database handle
    :return: user dict
    """

    if user_id is None:
        return None

    cursor = sqlite_db.cursor()
    query = "SELECT * FROM users WHERE id='{}'".format(user_id)
    cursor.execute(query)

    users = cursor.fetchall()

    if len(users) > 1:
        raise Exception('Multiple users found for single node ID')

    if users:
        user_obj = {}
        for key in users[0].keys():
            user_obj[key] = users[0][key]
        user_obj['institutions'] = json.loads(user_obj['institutions'])
        return user_obj

    user = User.load(user_id)
    if user is None:
        return None

    institutions = [
        {'id': inst._id, 'name': inst.name, 'logo_path': inst.logo_path}
        for inst in user.affiliated_institutions
    ] if user else []

    query = "INSERT INTO users (id, entry_point, locale, timezone, institutions) VALUES ('{id}', '{entry_point}', '{locale}', '{timezone}', '{institutions}');".format(
        id=user_id,
        entry_point=None if user is None else get_entry_point(user),
        locale=getattr(user, 'locale', ''),
        timezone=getattr(user, 'timezone', ''),
        institutions=json.dumps(institutions),
    )
    cursor.execute(query)
    sqlite_db.commit()
    return get_or_create_user(user_id, sqlite_db)


def get_or_create_node(node_id, sqlite_db):
    """Gets an OSF node from the sqlite cache.  If not found, pulls the node info from mongo and
    saves it.

    :param node_id: OSF node id (e.g. 'mst3k')
    :param sqlite_db: SQLite3 database handle
    :return: node dict
    """

    if node_id is None:
        return None

    cursor = sqlite_db.cursor()
    query = "SELECT * FROM nodes WHERE id='{}'".format(node_id)
    cursor.execute(query)

    nodes = cursor.fetchall()

    if len(nodes) > 1:
        raise Exception("Multiple nodes found for single node ID")

    if nodes:
        return nodes[0]

    node = Node.load(node_id)
    if node is None:
        return None

    node_public_date = None
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

    cursor.execute(
        u'INSERT INTO nodes (id, title, category, made_public_date) VALUES (?, ?, ?, ?)',
        (node_id, getattr(node, 'title'), getattr(node, 'category'), node_public_date)
    )
    sqlite_db.commit()
    return get_or_create_node(node_id, sqlite_db)


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

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    scripts_utils.add_file_logger(logger, __file__)
    force = '--force' in sys.argv
    main(force=force)
