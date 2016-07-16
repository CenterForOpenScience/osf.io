import json
import uuid
from binascii import b2a_hex
from socket import inet_ntoa
from datetime import datetime

import MySQLdb

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings as script_settings


NULL_IP = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
URL_PREFIX = ['http://', 'http://www.', 'https://', 'https://www.']


def migrate_data(mysql_db):
    """This script extracts pageview data from the OSF Piwik db and outputs the results
    to a dumpfile.

    :param mysql_db: MySQLdb connection to Piwik  database
    :return:
    """

    my_cursor = mysql_db.cursor(MySQLdb.cursors.DictCursor)
    my_cursor.execute("SET NAMES 'utf8'")
    my_cursor.execute(
        "SET sql_mode = 'ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_AUTO_VALUE_ON_ZERO,"
        "NO_ZERO_DATE,NO_ZERO_IN_DATE';"
    )


    history_file = utils.get_history_for('extract', 'w')
    output_file = open(utils.get_dir_for('extract') + '/' + script_settings.EXTRACT_FILE, 'w')

    count = 0
    last_count = 0

    history_file.write('Run ID: {}\n'.format(uuid.uuid4()))
    history_file.write('Beginning extraction at: {}Z\n'.format(datetime.utcnow()))
    visit_cursor = get_visits(mysql_db)
    visit = visit_cursor.fetchone()
    while visit is not None:
        action_cursor = get_actions_for_visit(mysql_db, visit['idvisit'])
        action = action_cursor.fetchone()

        while action is not None:

            # piwik stores searches weird.
            if action['page_title_type'] and action['page_title_type'] == 8:
                action['page_url'] = 'staging.osf.io/search/?q=' + action['page_title']
                action['page_url_prefix'] = 2
                action['page_title'] = 'OSF | Search'

            pageview = {
                'visit': {
                    'id': visit['idvisit'],
                    'visitor_id': b2a_hex(visit['idvisitor']),
                    'visitor_returning': visit['visitor_returning'],
                    'ip_addr': None if visit['location_ip'] == NULL_IP else inet_ntoa(visit['location_ip']),
                    'user_id': visit['user_id'],
                    'ua': {
                        'os': visit['config_os'],
                        'browser': {
                            'version': visit['config_browser_version'],
                            'name': visit['config_browser_name'],
                        },
                        'screen': visit['config_resolution'],
                    },
                },
                'action': {
                    'id': action['visit_action_id'],
                    'parent_node_id': action['parent_node_id'],
                    'node_id': action['node_id'],
                    'node_tags': action['node_tags'],
                    'page': {
                        'url': action['page_url'],
                        'url_prefix': None if action['page_url_prefix'] is None else URL_PREFIX[action['page_url_prefix']],
                        'url_id': action['page_url_id'],
                        'url_type': action['page_url_type'],
                        'title': action['page_title'],
                        'title_id': action['page_title_id'],
                        'title_type': action['page_title_type'],
                        'is_search': True if action['page_title_type'] and action['page_title_type'] == 8 else False,
                    },
                    'referrer': visit['referer_url'],
                    'timestamp': str(action['server_time']),
                },
            }

            output_file.write(json.dumps(pageview) + '\n')
            history_file.write('\tLast action written timestamp: ' + str(action['server_time']) + '\n')
            count += 1
            action = action_cursor.fetchone()

        visit = visit_cursor.fetchone()

    history_file.write('Finished extraction at: {}Z\n'.format(datetime.utcnow()))
    history_file.write('Final count was: {}\n'.format(count))
    print("Final count is: {}".format(count))
    history_file.close()
    output_file.close()


def get_visits(mysql_db):
    """Get individual user visits to the OSF.  One visit may include multiple pageviews, which
    will be fetched by the get_actions_for_visit() function.

    We don't actually save the ``user_name`` field, it's just here for documentation purposes.

    Unused:
      visit_goal_buyer, visit_goal_converted,
      custom_var_{v3,v4,v5} don't appear to be used.

    Ignored:
      log_visit.custom_var_v2 AS user_name
        not saved, just to help with debugging

      log_visit.visit_exit_idaction_name, visit_exit_idaction_url
        track where user goes when exiting site.  Not currently being tracked.

    """

    query = '''
SELECT
  log_visit.idvisit,
  log_visit.idvisitor,
  log_visit.location_ip,
  log_visit.config_os,
  log_visit.config_browser_version,
  log_visit.config_browser_name,
  log_visit.config_resolution,
  log_visit.referer_url,
  log_visit.visitor_returning,
  log_visit.custom_var_v1 AS user_id,
  log_visit.custom_var_v2 AS user_name
FROM piwik_log_visit AS log_visit
WHERE log_visit.idsite in (1)
GROUP BY log_visit.idvisit
ORDER BY log_visit.idsite, log_visit.visit_last_action_time DESC
'''

    cursor = mysql_db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query)
    return cursor


def get_actions_for_visit(mysql_db, visit_id):
    """Get actions for a specific Piwik visit. Each pageview is considered a separate action.
    Searches are also considered an action, but are stored a little bit differently from pageviews.

    Piwik Schema Documentation:

    Visit Actions: https://developer.piwik.org/guides/persistence-and-the-mysql-backend#visit-actions
    Log Actions: https://developer.piwik.org/guides/persistence-and-the-mysql-backend#action-types

    Notes:

    Excludes log_action types 2 and 3.  Type 2 is links to external sites.  Type 3 is downloads,
    but seems to be incorrect.  Only one action of type 3 appears in the staging data and that has
    an access token?  Only compare if log_action IS NOT NULL, otherwise we will miss out on
    searches (page_url.type IS NULL AND page_title.type = 8).

    idaction_event_action, idaction_event_category, idaction_content_interaction,
    idaction_content_name, idaction_content_piece, idaction_content_target, and
    custom_var_{k,v}{1,5} all appear to be unused.

    server_time is yyyy-mm-dd hh:mm::ss in UTC

    page_url_prefix is an integer key for scheme.

    Removed:
      visit_action.time_spent_ref_action AS time_spent
         Time spent on page.  Not currently tracking this
      visit_action.custom_float AS response_time
         Time spent responding to request. Not currently tracking this.

    :param mysql_db: Piwik MySQLdb connection
    :param visit_id: Piwik Visit Id, obtained from MySQL rows
    :return: dict of all actions for a given website, each action also a dict
    """

    query = '''
SELECT
  page_url.name AS page_url,
  page_url.url_prefix AS page_url_prefix,
  page_url.type AS page_url_type,
  page_url.idaction AS page_url_id,

  page_title.name AS page_title,
  page_title.type AS page_title_type,
  page_title.idaction AS page_title_id,

  visit_action.idlink_va AS visit_action_id,
  visit_action.server_time AS server_time,
  visit_action.custom_var_k2, visit_action.custom_var_v2 AS parent_node_id,
  visit_action.custom_var_k3, visit_action.custom_var_v3 AS node_id,
  visit_action.custom_var_k4, visit_action.custom_var_v4 AS node_tags
FROM piwik_log_link_visit_action AS visit_action
  LEFT JOIN piwik_log_action AS page_url ON visit_action.idaction_url=page_url.idaction
  LEFT JOIN piwik_log_action AS page_title ON visit_action.idaction_name=page_title.idaction
WHERE visit_action.idvisit='{}'
  AND (page_url.type IS NULL OR (page_url.type != 2 AND page_url.type != 3))
ORDER BY server_time ASC;
'''.format(visit_id)

    cursor = mysql_db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query)
    return cursor


def main():
    try:
        mysql_db = MySQLdb.connect(
            host=script_settings.PIWIK_DB_HOST, port=script_settings.PIWIK_DB_PORT,
            user=script_settings.PIWIK_DB_USER, passwd=script_settings.PIWIK_DB_PASSWORD,
            db=script_settings.PIWIK_DB_NAME
        )
    except MySQLdb.Error as err:
        print "MySQL Error [%d]: %s" % (err.args[0], err.args[1])
    else:
        migrate_data(mysql_db=mysql_db)
        mysql_db.close()


if __name__ == "__main__":
    main()

