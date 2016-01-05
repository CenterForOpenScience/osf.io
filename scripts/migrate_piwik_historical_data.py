import mysql.connector
from mysql.connector import errorcode

def main():
    config = {
        'user': 'root',
        'password': 'root',
        'host': '127.0.0.1',
        'port': '8889',
        'database': 'piwik'
    }

    try:
        cnx = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:

        cursor = cnx.cursor()

        query = "SET sql_mode = 'ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_AUTO_VALUE_ON_ZERO,NO_ZERO_DATE,NO_ZERO_IN_DATE'; SELECT sub.* FROM (SELECT log_visit.* FROM piwik_log_visit AS log_visit WHERE log_visit.idsite in (1) AND log_visit.visit_last_action_time >= '2015-11-30 00:00:00' AND  log_visit.visit_last_action_time <= '2015-12-01 00:00:00' ORDER BY idsite, visit_last_action_time DESC LIMIT 100) AS sub GROUP BY sub.idvisit ORDER BY sub.visit_last_action_time DESC;"
        cursor.execute(query, multi=True)
        print cursor.with_rows

        query = ("USE piwik; "
                 "SELECT COALESCE(log_action_event_category.type, log_action.type, log_action_title.type) AS type, "
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
                 "WHERE log_link_visit_action.idvisit = '206' "
                 "ORDER BY server_time ASC "
                 "LIMIT 0, 500;")

        cnx.close()

if __name__ == "__main__":
    main()
