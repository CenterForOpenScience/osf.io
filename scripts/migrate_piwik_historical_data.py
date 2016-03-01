import MySQLdb
from socket import inet_ntoa
from binascii import b2a_hex
import pprint
from keen import KeenClient
import urlparse

def main():

    keen_client = KeenClient(
        project_id='56abc1c759949a6734c3f32b',
        write_key='248de5ffaf1c829bf74dc6e4e0fc3af6beaa7f5194c2d163699213b66e8cf1fbc41a1adc1dd9b6ec3681ac31584bd0c9847c8d9ca223e44e99e60af219be19c55a9261437020069f92c5825cc2995cba57976ed485e3a9f314e3a1d21d032e53'
    )

    try:
        db = MySQLdb.connect(host='127.0.0.1', port=8889, user='root', passwd='root', db='piwikOrig')
    except MySQLdb.Error as err:
        print "MySQL Error [%d]: %s" % (err.args[0], err.args[1])
    else:

        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        query = "SET NAMES 'utf8'"
        cursor.execute(query)

        query = "SET sql_mode = 'ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_AUTO_VALUE_ON_ZERO,NO_ZERO_DATE,NO_ZERO_IN_DATE';"
        cursor.execute(query)

        query = "SELECT sub.* FROM (SELECT log_visit.* FROM piwik_log_visit AS log_visit WHERE log_visit.idsite in (1) AND log_visit.visit_last_action_time >= '2016-02-01 00:00:00' ORDER BY idsite, visit_last_action_time DESC LIMIT 100) AS sub GROUP BY sub.idvisit ORDER BY sub.visit_last_action_time DESC;"
        cursor.execute(query)

        rows = cursor.fetchall()
        visit = {}
        pageview = {}
        count = 0;

        for row in rows:

            visit['browser_name'] = row['config_browser_name']
            visit['browser_version'] = row['config_browser_version']
            visit['operating_system'] = row['config_os']
            visit['config_id'] = b2a_hex(row['config_id'])
            visit['resolution'] = row['config_resolution']
            #Custom Variables
            if row['custom_var_k1']:
                visit[row['custom_var_k1']] = row['custom_var_v1']
            if row['custom_var_k2']:
                visit[row['custom_var_k2']] = row['custom_var_v2']
            if row['custom_var_k3']:
                visit[row['custom_var_k3']] = row['custom_var_v3']
            if row['custom_var_k4']:
                visit[row['custom_var_k4']] = row['custom_var_v4']
            if row['custom_var_k5']:
                visit[row['custom_var_k5']] = row['custom_var_v5']
            visit['site_id'] = row['idsite']
            visit_id = row['idvisit']
            visit['visit_id'] = row['idvisit']
            visit['piwik_visitor_id'] = b2a_hex(row['idvisitor'])
            visit['browser_lang'] = row['location_browser_lang']
            visit['country'] = row['location_country']
            if row['location_ip'] == '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':
                visit['ip'] = ''
            else:
                visit['ip'] = inet_ntoa(row['location_ip'])
            visit['location_provider'] = row['location_provider']
            visit['region'] = row['location_region']
            visit['referrer_keyword'] = row['referer_keyword']
            visit['referrer_name'] = row['referer_name']
            visit['referrer_type'] = row['referer_type']
            visit['referrer_url'] = row['referer_url']
            visit['first_action_time'] = str(row['visit_first_action_time'])
            visit['last_action_time'] = str(row['visit_last_action_time'])
            visit['actions'] = row['visit_total_actions']
            visit['searches'] = row['visit_total_searches']
            visit['visitor_visit_count'] = row['visitor_count_visits']
            visit['days_since_first_visit'] = row['visitor_days_since_first']
            visit['days_since_last_visit'] = row['visitor_days_since_last']
            visit['visit_length'] = row['visit_total_time']
            visit['visit_localtime'] = str(row['visitor_localtime'])
            if row['visitor_returning'] == 1:
                visit['visitor_type'] = 'returning'
            else:
                visit['visitor_type'] = 'new'

            keen_client.add_event('test_visits', visit)

            #Get actions for each visit
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
                     "WHERE log_link_visit_action.idvisit = '" + str(visit_id) + "'"
                     "ORDER BY server_time ASC "
                     "LIMIT 0, 500;")

            cursor.execute(query)
            rows = cursor.fetchall()
            if count < 1000:
                for row in rows:
                    #Custom Variables
                    pageview['generation_time'] = row['custom_float']
                    if row['custom_var_k1']:
                        pageview[row['custom_var_k1']] = row['custom_var_v1']
                    if row['custom_var_k2']:
                        pageview[row['custom_var_k2']] = row['custom_var_v2']
                    if row['custom_var_k3']:
                        pageview[row['custom_var_k3']] = row['custom_var_v3']
                    if row['custom_var_k4']:
                        pageview[row['custom_var_k4']] = row['custom_var_v4']
                    if row['custom_var_k5']:
                        pageview[row['custom_var_k5']] = row['custom_var_v5']
                    pageview['page_title'] = row['pageTitle']
                    pageview['server_time'] = str(row['serverTimePretty'])
                    pageview['url'] = row['url']
                    if row['url']:
                        url_parsed = urlparse.urlparse(row['url'])
                        pageview['url_parsed'] = {
                            'scheme' : url_parsed.scheme,
                            'netloc' : url_parsed.netloc,
                            'path' :url_parsed.path,
                            'params' : url_parsed.params,
                            'query' : url_parsed.query,
                            'query_params': dict(urlparse.parse_qsl(url_parsed.query)),
                            'fragment' : url_parsed.fragment,
                            'hostname' : url_parsed.hostname,
                            'port' : url_parsed.port
                        }
                    pageview['time_spent'] = row['timeSpentRef']

                    keen_client.add_event('test_pageviews', pageview)
        db.close()

if __name__ == "__main__":
    main()
