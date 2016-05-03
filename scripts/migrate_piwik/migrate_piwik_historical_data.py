import MySQLdb
from socket import inet_ntoa
from binascii import b2a_hex
from keen import KeenClient
import uuid
import datetime
import sqlite3
from settings import settings as script_settings

from website.models import User

def db_setup():

    conn = sqlite3.connect('piwik_users.sqlite')

    cursor = conn.cursor()

    cursor.execute('CREATE TABLE matched_ids (piwik_id TEXT, new_id TEXT)')

    conn.commit()
    conn.close()


def migrate_data(mysql_db, sqlite_db, start_date, end_date):

    my_cursor = mysql_db.cursor(MySQLdb.cursors.DictCursor)
    sqlite_cursor = sqlite_db.cursor()

    keen_client = KeenClient(
        project_id=script_settings.PROJECT_ID,
        write_key=script_settings.WRITE_KEY
    )

    query = "SET NAMES 'utf8'"
    my_cursor.execute(query)

    query = "SET sql_mode = 'ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_AUTO_VALUE_ON_ZERO,NO_ZERO_DATE,NO_ZERO_IN_DATE';"
    my_cursor.execute(query)

    count = 0
    while start_date != end_date and count < 1:
        history_file = open('timestamps.txt', 'w')
        previous_day = start_date - datetime.timedelta(days=1)

        history_file.write('Migrating ' + str(previous_day) + ' to ' + str(start_date) + '\n')

        visits = get_visits(my_cursor, previous_day, start_date)

        for visit in visits:
            if count < 1:
                pageviews = []

                visit_id = visit['idvisit']
                session_id = str(uuid.uuid4())
                user_id = b2a_hex(visit['idvisitor'])

                new_id = get_or_create_new_id(user_id, sqlite_cursor, sqlite_conn=sqlite_db)

                actions = get_actions_for_visit(my_cursor, visit_id)

                history_file.write('Migrating actions for visitid ' + str(visit_id) + ':\n')

                for action in actions:

                    pageview = {
                        'pageUrl': parse_page_url(action['url']) or None,  # pageview
                        'keenUserId': new_id,  # idvisitor
                        'sessionId': session_id,  # random val
                        'pageTitle': action['pageTitle'],  # pageview
                        'userAgent': None,  # manual
                        'parsedUserAgent': {
                            'device': {
                                'family': None
                            },
                            'os': {
                                'major': None,
                                'patch_minor': None,
                                'minor': None,
                                'family': parse_os_family(visit['config_os']), #Needs parser
                                'patch': None
                            },
                            'browser': {
                              'major': visit['config_browser_version'].split('.')[0] if visit['config_browser_version'] else None,
                              'minor': visit['config_browser_version'].split('.')[1] if visit['config_browser_version'] else None,
                              'family': parse_browser_family(visit['config_browser_name']), #Needs parser
                              'patch': None
                            },
                            'resolution': visit['config_resolution']
                        },
                        'referrer': {
                            'url': visit['referer_url'] or None  # visit
                        },
                        'ipAddress': None if visit['location_ip'] == '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' else inet_ntoa(visit['location_ip']),  # visit
                        'returning': True if visit['visitor_returning'] else False,  # visit
                        'keen': {
                            'addons': [
                                {
                                    'name': 'keen:ip_to_geo',
                                    'input': {
                                        'ip': 'ipAddress'
                                    },
                                    'output': 'ipGeoInfo'
                                },
                                {
                                    'name': 'keen:referrer_parser',
                                    'input': {
                                        'referrer_url': 'referrer.url',
                                        'page_url': 'pageUrl'
                                    },
                                    'output': 'referrer.info'
                                },
                                {
                                    'name': 'keen:url_parser',
                                    'input': {
                                        'url': 'pageUrl'
                                    },
                                    'output': 'parsedPageUrl'
                                },
                                {
                                    'name': 'keen:url_parser',
                                    'input': {
                                        'url': 'referrer.url'
                                    },
                                    'output': 'parsedReferrerUrl'
                                }
                            ]
                        }
                    }

                    if visit['custom_var_v1']:
                        user = User.load(str(visit['custom_var_v1'])) or None
                        pageview['user'] = {
                            'id': visit['custom_var_v1'],
                            'systemTags': get_entry_point(user.system_tags) if user else None
                        }

                    pageview['keen']['timestamp'] = str(action['serverTimePretty'])

                    if action['custom_var_v3']:
                        pageview['node'] = {
                            'id': action['custom_var_v3'],
                            'title': None,
                            'type': None,
                            'tags': [tag for tag in action['custom_var_v4'].split(',')]
                        }

                    history_file.write('\tLast action written timestamp: ' + str(action['serverTimePretty']) + '\n')
                    pageviews.append(pageview)
                    count += 1
                print count
                print pageviews
                keen_client.add_events({'RPP Pageviews': pageviews})

        print("Finished day " + str(start_date), count)
        start_date = start_date - datetime.timedelta(days=1)


def get_visits(cursor, previous_day, current_day):

    query = "SELECT sub.* FROM (SELECT log_visit.* FROM piwik_log_visit AS log_visit WHERE log_visit.idsite in (1) AND log_visit.visit_last_action_time >= '" + str(previous_day) + \
            "' AND log_visit.visit_last_action_time <= '" + str(current_day) + \
            "' ORDER BY idsite, visit_last_action_time DESC) AS sub GROUP BY sub.idvisit ORDER BY sub.visit_last_action_time DESC;"
    cursor.execute(query)

    return cursor.fetchall()


def get_actions_for_visit(cursor, visit_id):

    query = ("SELECT COALESCE(log_action_event_category.type, log_action.type, log_action_title.type) AS type, "
                 "log_action.name AS url, "
                 "log_action.url_prefix, "
                 "log_action_title.name AS pageTitle, "
                 "log_action.idaction AS pageIdAction, "
                 "log_link_visit_action.idlink_va, "
                 "log_link_visit_action.server_time as serverTimePretty, "
                 "log_link_visit_action.time_spent_ref_action as timeSpentRef, "
                 "log_link_visit_action.idlink_va AS pageId, "
                 "log_link_visit_action.custom_float, "
                 "custom_var_k1, custom_var_v1, custom_var_k2, custom_var_v2, custom_var_k3, custom_var_v3, custom_var_k4, custom_var_v4, custom_var_k5, custom_var_v5, "
                 "log_action_event_category.name AS eventCategory, "
                 "log_action_event_action.name as eventAction "
                 "FROM piwik_log_link_visit_action AS log_link_visit_action "
                 "LEFT JOIN piwik_log_action AS log_action "
                 "ON  log_link_visit_action.idaction_url = log_action.idaction "
                 "LEFT JOIN piwik_log_action AS log_action_title "
                 "ON  log_link_visit_action.idaction_name = log_action_title.idaction "
                 "LEFT JOIN piwik_log_action AS log_action_event_category "
                 "ON  log_link_visit_action.idaction_event_category = log_action_event_category.idaction "
                 "LEFT JOIN piwik_log_action AS log_action_event_action "
                 "ON  log_link_visit_action.idaction_event_action = log_action_event_action.idaction "
                 "WHERE log_link_visit_action.idvisit = '" + str(visit_id) + "' ORDER BY server_time ASC; ")

    cursor.execute(query)
    return cursor.fetchall()


def get_or_create_new_id(user_id, sqlite_cursor, sqlite_conn):
    query = "SELECT * FROM matched_ids WHERE piwik_id='{p_id}'".format(p_id=user_id)
    sqlite_cursor.execute(query)

    new_id = sqlite_cursor.fetchall()

    if len(new_id) > 1:
        raise Exception("Multiple ID's found for single Piwik User ID")

    if not new_id:
        new_id = uuid.uuid4()
        query = "INSERT INTO matched_ids (piwik_id, new_id) VALUES ('{p_id}', '{n_id}');".format(p_id=str(user_id), n_id=str(new_id))
        sqlite_cursor.execute(query)
        sqlite_conn.commit()
        return str(new_id)

    return str(new_id[0][1])


def parse_os_family(os_name):

    if os_name == 'UNK':
        return 'Unknown'

    parsed_os_family = None



    legacy_keys = {
        'IPA': 'IOS',
        'IPH': 'IOS',
        'IPD': 'IOS',
        'WIU': 'WII',
        '3DS': 'NDS',
        'DSI': 'NDS',
        'PSV': 'PSP',
        'MAE': 'SMG',
    }

    if os_name in legacy_keys:
        parsed_os_family = legacy_keys[os_name]

    os_keys = {
        'AIX':  'AIX',
        'AND':  'Android',
        'AMG':  'AmigaOS',
        'ATV':  'Apple TV',
        'ARL':  'Arch Linux',
        'BTR':  'BackTrack',
        'SBA':  'Bada',
        'BEO':  'BeOS',
        'BLB':  'BlackBerry OS',
        'QNX':  'BlackBerry Tablet OS',
        'BMP':  'Brew',
        'CES':  'CentOS',
        'COS':  'Chrome OS',
        'CYN':  'CyanogenMod',
        'DEB':  'Debian',
        'DFB':  'DragonFly',
        'FED':  'Fedora',
        'FOS':  'Firefox OS',
        'BSD':  'FreeBSD',
        'GNT':  'Gentoo',
        'GTV':  'Google TV',
        'HPX':  'HP-UX',
        'HAI':  'Haiku OS',
        'IRI':  'IRIX',
        'INF':  'Inferno',
        'KNO':  'Knoppix',
        'KBT':  'Kubuntu',
        'LIN':  'Linux',
        'LBT':  'Lubuntu',
        'VLN':  'VectorLinux',
        'MAC':  'Mac OS X',
        'MAE':  'Maemo',
        'MDR':  'Mandriva',
        'SMG':  'MeeGo',
        'MCD':  'MocorDroid',
        'MIN':  'Mint',
        'MLD':  'MildWild',
        'MOR':  'MorphOS',
        'NBS':  'NetBSD',
        'MTK':  'MTK / Nucleus',
        'WII':  'Nintendo',
        'NDS':  'Nintendo Mobile',
        'OS2':  'OS/2',
        'T64':  'OSF1',
        'OBS':  'OpenBSD',
        'PSP':  'PlayStation Portable',
        'PS3':  'PlayStation',
        'RHT':  'Red Hat',
        'ROS':  'RISC OS',
        'RZD':  'RazoDroiD',
        'SAB':  'Sabayon',
        'SSE':  'SUSE',
        'SAF':  'Sailfish OS',
        'SLW':  'Slackware',
        'SOS':  'Solaris',
        'SYL':  'Syllable',
        'SYM':  'Symbian',
        'SYS':  'Symbian OS',
        'S40':  'Symbian OS Series 40',
        'S60':  'Symbian OS Series 60',
        'SY3':  'Symbian^3',
        'TDX':  'ThreadX',
        'TIZ':  'Tizen',
        'UBT':  'Ubuntu',
        'WTV':  'WebTV',
        'WIN':  'Windows <Unknown Version>',
        'W10':  'Windows 10',
        'W2K':  'Windows 2000',
        'W31':  'Windows 3.1',
        'WI7':  'Windows 7',
        'WI8':  'Windows 8',
        'W81':  'Windows 8.1',
        'W95':  'Windows 95',
        'W98':  'Windows 98',
        'WME':  'Windows ME',
        'WNT':  'Windows NT',
        'WS3':  'Windows Server 2003',
        'WVI':  'Windows Vista',
        'WXP':  'Windows XP',
        'WCE':  'Windows CE',
        'WMO':  'Windows Mobile',
        'WPH':  'Windows Phone',
        'WRT':  'Windows RT',
        'XBX':  'Xbox',
        'XBT':  'Xubuntu',
        'YNS':  'YunOs',
        'IOS':  'iOS',
        'POS':  'palmOS',
        'WOS':  'webOS'
        }

    if parsed_os_family:
        return os_keys[parsed_os_family]
    elif os_name in os_keys:
        return os_keys[os_name]
    else:
        return 'Unknown'


def parse_browser_family(browser_name):

    if browser_name == 'UNK':
        return 'Unknown'

    browser_codes = {
        '36':  '360 Phone Browser',
        '3B':  '360 Browser',
        'AA':  'Avant Browser',
        'AB':  'ABrowse',
        'AF':  'ANT Fresco',
        'AG':  'ANTGalio',
        'AM':  'Amaya',
        'AO':  'Amigo',
        'AN':  'Android Browser',
        'AR':  'Arora',
        'AV':  'Amiga Voyager',
        'AW':  'Amiga Aweb',
        'AT':  'Atomic Web Browser',
        'BB':  'BlackBerry Browser',
        'BD':  'Baidu Browser',
        'BS':  'Baidu Spark',
        'BE':  'Beonex',
        'BJ':  'Bunjalloo',
        'BR':  'Brave',
        'BX':  'BrowseX',
        'CA':  'Camino',
        'CC':  'Coc Coc',
        'CD':  'Comodo Dragon',
        'CX':  'Charon',
        'CF':  'Chrome Frame',
        'CH':  'Chrome',
        'CI':  'Chrome Mobile iOS',
        'CK':  'Conkeror',
        'CM':  'Chrome Mobile',
        'CN':  'CoolNovo',
        'CO':  'CometBird',
        'CP':  'ChromePlus',
        'CR':  'Chromium',
        'CS':  'Cheshire',
        'DE':  'Deepnet Explorer',
        'DF':  'Dolphin',
        'DI':  'Dillo',
        'EL':  'Elinks',
        'EB':  'Element Browser',
        'EP':  'Epiphany',
        'ES':  'Espial TV Browser',
        'FB':  'Firebird',
        'FD':  'Fluid',
        'FE':  'Fennec',
        'FF':  'Firefox',
        'FL':  'Flock',
        'FW':  'Fireweb',
        'FN':  'Fireweb Navigator',
        'GA':  'Galeon',
        'GE':  'Google Earth',
        'HJ':  'HotJava',
        'IA':  'Iceape',
        'IB':  'IBrowse',
        'IC':  'iCab',
        'ID':  'IceDragon',
        'IW':  'Iceweasel',
        'IE':  'IE',
        'IM':  'IE Mobile',
        'IR':  'Iron',
        'JS':  'Jasmine',
        'JI':  'Jig Browser',
        'KI':  'Kindle Browser',
        'KM':  'K-meleon',
        'KO':  'Konqueror',
        'KP':  'Kapiko',
        'KY':  'Kylo',
        'KZ':  'Kazehakase',
        'LB':  'Liebao',
        'LG':  'LG Browser',
        'LI':  'Links',
        'LU':  'LuaKit',
        'LS':  'Lunascape',
        'LX':  'Lynx',
        'MB':  'MicroB',
        'MC':  'NCSA Mosaic',
        'ME':  'Mercury',
        'MF':  'Mobile Safari',
        'MI':  'Midori',
        'MU':  'MIUI Browser',
        'MS':  'Mobile Silk',
        'MX':  'Maxthon',
        'NB':  'Nokia Browser',
        'NO':  'Nokia OSS Browser',
        'NV':  'Nokia Ovi Browser',
        'NF':  'NetFront',
        'NL':  'NetFront Life',
        'NP':  'NetPositive',
        'NS':  'Netscape',
        'OB':  'Obigo',
        'OD':  'Odyssey Web Browser',
        'OF':  'Off By One',
        'OE':  'ONE Browser',
        'OI':  'Opera Mini',
        'OM':  'Opera Mobile',
        'OP':  'Opera',
        'ON':  'Opera Next',
        'OR':  'Oregano',
        'OV':  'Openwave Mobile Browser',
        'OW':  'OmniWeb',
        'OT':  'Otter Browser',
        'PL':  'Palm Blazer',
        'PM':  'Pale Moon',
        'PR':  'Palm Pre',
        'PU':  'Puffin',
        'PW':  'Palm WebPro',
        'PX':  'Phoenix',
        'PO':  'Polaris',
        'PS':  'Microsoft Edge',
        'QQ':  'QQ Browser',
        'RK':  'Rekonq',
        'RM':  'RockMelt',
        'SA':  'Sailfish Browser',
        'SC':  'SEMC-Browser',
        'SE':  'Sogou Explorer',
        'SF':  'Safari',
        'SH':  'Shiira',
        'SK':  'Skyfire',
        'SS':  'Seraphic Sraf',
        'SL':  'Sleipnir',
        'SM':  'SeaMonkey',
        'SN':  'Snowshoe',
        'SR':  'Sunrise',
        'SP':  'SuperBird',
        'SX':  'Swiftfox',
        'TZ':  'Tizen Browser',
        'UC':  'UC Browser',
        'VI':  'Vivaldi',
        'VB':  'Vision Mobile Browser',
        'WE':  'WebPositive',
        'WO':  'wOSBrowser',
        'WT':  'WeTab Browser',
        'YA':  'Yandex Browser',
        'XI':  'Xiino'
    }

    if browser_name in browser_codes:
        return browser_codes[browser_name]
    else:
        return 'Unknown'


def parse_page_url(page_url):

    if page_url:
        if page_url.startswith('osf.io'):
            return 'http://' + page_url
        else:
            return page_url
    else:
        return None


def get_entry_point(system_tags):
    """
    Given the user system_tags, return the user entry point (osf, osf4m, prereg, institution)
    In case of multiple entry_points existing in the system_tags, return only the first one.
    """
    entry_points = ['osf4m', 'prereg_challenge_campaign', 'institution_campaign']
    for i in system_tags:
        if i in entry_points:
            return i
        else:
            return 'osf'

def main():

    start_date = datetime.datetime.strptime('2016-02-02 00:00:00', '%Y-%m-%d %H:%M:%S')
    end_date = datetime.datetime.strptime('2016-02-01 00:00:00', '%Y-%m-%d %H:%M:%S')

    try:
        mysql_db = MySQLdb.connect(host=script_settings.PIWIK_DB_HOST, port=script_settings.PIWIK_DB_PORT, user=script_settings.PIWIK_DB_USER, passwd=script_settings.PIWIK_DB_PASSWORD, db=script_settings.PIWIK_DB_NAME)
        sqlite_db = sqlite3.connect('piwik_users.sqlite')
    except MySQLdb.Error as err:
        print "MySQL Error [%d]: %s" % (err.args[0], err.args[1])
    else:
        migrate_data(mysql_db=mysql_db, sqlite_db=sqlite_db, start_date=start_date, end_date=end_date)
        mysql_db.close()
        sqlite_db.close()


if __name__ == "__main__":
    main()
