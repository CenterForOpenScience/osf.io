import MySQLdb
from socket import inet_ntoa
from binascii import b2a_hex
import pprint

def main():
    config = {
        'user': 'root',
        'password': 'root',
        'host': '127.0.0.1',
        'port': '8889',
        'database': 'piwik',
        'use_unicode': False,
    }

    try:
        db = MySQLdb.connect(host='127.0.0.1', port=8889, user='root', passwd='root', db='piwik')
    except MySQLdb.Error as err:
        print "MySQL Error [%d]: %s" % (err.args[0], err.args[1])
    else:

        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        query = "SET NAMES 'utf8'"
        cursor.execute(query)

        query = "SET sql_mode = 'ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_AUTO_VALUE_ON_ZERO,NO_ZERO_DATE,NO_ZERO_IN_DATE';"
        cursor.execute(query)

        query = "SELECT sub.* FROM (SELECT log_visit.* FROM piwik_log_visit AS log_visit WHERE log_visit.idsite in (1) AND log_visit.visit_last_action_time >= '2016-01-05 00:00:00' ORDER BY idsite, visit_last_action_time DESC LIMIT 100) AS sub GROUP BY sub.idvisit ORDER BY sub.visit_last_action_time DESC;"
        cursor.execute(query)

        rows = cursor.fetchall()
        keen_event = {}
        for row in rows:
            visit_id = row['idvisit']
            keen_event['config_id'] = b2a_hex(row['config_id'])
            if row['location_ip'] == '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':
                keen_event['ip'] = ''
            else:
                keen_event['ip'] = inet_ntoa(row['location_ip'])
            keen_event['visit_localtime'] = row['visitor_localtime']
            keen_event['operating_system'] = row['config_os']
            keen_event['referrer_url'] = row['referer_url']
            #Custom Variables
            if row['custom_var_k1']:
                keen_event[row['custom_var_k1']] = row['custom_var_v1']
            if row['custom_var_k2']:
                keen_event[row['custom_var_k2']] = row['custom_var_v2']
            if row['custom_var_k3']:
                keen_event[row['custom_var_k3']] = row['custom_var_v3']
            if row['custom_var_k4']:
                keen_event[row['custom_var_k4']] = row['custom_var_v4']
            if row['custom_var_k5']:
                keen_event[row['custom_var_k5']] = row['custom_var_v5']
            keen_event['browser_lang'] = row['location_browser_lang']
            if row['user_id']:
                keen_event['piwik_user_id'] = b2a_hex(row['user_id'])
            keen_event['country'] = row['location_country']
            keen_event['days_since_last_visit'] = row['visitor_days_since_last']
            keen_event['visit_id'] = row['idvisit']
            keen_event['searches'] = row['visit_total_searches']
            keen_event['visit_length'] = row['visit_total_time']
            keen_event['visit_count'] = row['visitor_count_visits']
            keen_event['site_id'] = row['idsite']
            keen_event['days_since_first_visit'] = row['visitor_days_since_first']
            keen_event['referrer_type'] = row['referer_type']
            keen_event['referrer_keyword'] = row['referer_keyword']
            keen_event['region'] = row['location_region']
            keen_event['referrer_name'] = row['referer_name']
            keen_event['resolution'] = row['config_resolution']
            keen_event['browser_eng'] = row['config_browser_engine']
            if row['visitor_returning'] == 1:
                keen_event['visitor_type'] = 'returning'
            else:
                keen_event['visitor_type'] = 'new'
            keen_event['browser_version'] = row['config_browser_version']
            keen_event['browser_name'] = row['config_browser_name']
            keen_event['actions'] = row['visit_total_actions']
            keen_event['first_action_time'] = row['visit_first_action_time']
            keen_event['os_version'] = row['config_os_version']
            keen_event['last_action_time'] = row['visit_last_action_time']
            keen_event['piwik_visitor_id'] = b2a_hex(row['idvisitor'])

            pprint.pprint(keen_event)

            # query = ("SELECT COALESCE(log_action_event_category.type, log_action.type, log_action_title.type) AS type, "
            #          "log_action.name AS url, "
            #          "log_action.url_prefix, "
            #          "log_action_title.name AS pageTitle, "
            #          "log_action.idaction AS pageIdAction, "
            #          "log_link_visit_action.idlink_va, "
            #          "log_link_visit_action.server_time as serverTimePretty, "
            #          "log_link_visit_action.time_spent_ref_action as timeSpentRef, "
            #          "log_link_visit_action.idlink_va AS pageId, "
            #          "log_link_visit_action.custom_float, "
            #          "custom_var_k1, custom_var_v1, custom_var_k2, custom_var_v2, custom_var_k3, custom_var_v3, custom_var_k4, custom_var_v4, custom_var_k5, custom_var_v5, "
            #          "log_action_event_category.name AS eventCategory, "
            #          "log_action_event_action.name as eventAction "
            #          "FROM piwik_log_link_visit_action AS log_link_visit_action "
            #          "LEFT JOIN piwik_log_action AS log_action "
            #          "ON  log_link_visit_action.idaction_url = log_action.idaction "
            #          "LEFT JOIN piwik_log_action AS log_action_title "
            #          "ON  log_link_visit_action.idaction_name = log_action_title.idaction "
            #          "LEFT JOIN piwik_log_action AS log_action_event_category "
            #          "ON  log_link_visit_action.idaction_event_category = log_action_event_category.idaction "
            #          "LEFT JOIN piwik_log_action AS log_action_event_action "
            #          "ON  log_link_visit_action.idaction_event_action = log_action_event_action.idaction "
            #          "WHERE log_link_visit_action.idvisit = '" + str(visit_id) + "'rrr"
            #          "ORDER BY server_time ASC "
            #          "LIMIT 0, 500;")
            # cursor.execute(query)
            # rows = cursor.fetchall()
            #
            # for row in rows:
            #     pprint.pprint(row)
            #     print

        db.close()

if __name__ == "__main__":
    main()
