# encoding: utf-8

from dateutil.relativedelta import relativedelta


TABULATE_EMAILS_NODE_ID = 'ejnwh'  # Daily updates project
TABULATE_EMAILS_USER_ID = 'jm6t4'  # Daily updates user
TABULATE_EMAILS_FILE_NAME = 'daily-users.csv'
TABULATE_EMAILS_CONTENT_TYPE = 'text/csv'
TABULATE_EMAILS_TIME_DELTA = relativedelta(days=1)

TABULATE_LOGS_RESULTS_COLLECTION = 'logmetrics'
TABULATE_LOGS_NODE_ID = 'ejnwh'  # Daily updates project
TABULATE_LOGS_USER_ID = 'jm6t4'  # Daily updates user
TABULATE_LOGS_FILE_NAME = 'log-counts.csv'
TABULATE_LOGS_CONTENT_TYPE = 'text/csv'
TABULATE_LOGS_TIME_OFFSET = relativedelta(days=1)

ANALYTICS_LOGS_NODE_ID = 'ejnwh'
ANALYTICS_LOGS_USER_ID = 'jm6t6'
