import logging

# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [
    'factory.generate',
    'factory.containers',
    'website.search.elastic_search',
    'framework.analytics',
    'framework.auth.core',
    'website.mails',
    'website.search_migration.migrate',
    'website.util.paths',
    'api.caching.tasks',
    'website.notifications.listeners',
    'website.archiver.tasks',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
