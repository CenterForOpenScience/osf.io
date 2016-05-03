from admin.base.settings import KEEN_PROJECT_ID, KEEN_READ_KEY, KEEN_WRITE_KEY

KEEN_CREDENTIALS = {
    'keen_ready': False
}

if KEEN_CREDENTIALS['keen_ready']:
    KEEN_CREDENTIALS.update({
        'keen_project_id': KEEN_PROJECT_ID,
        'keen_read_key': KEEN_READ_KEY,
        'keen_write_key': KEEN_WRITE_KEY
    })


# TODO: when Keen is ready, use of settings instead
# from website import settings as osf_settings
# KEEN_CREDENTIALS = {
#     'keen_ready': osf_settings.KEEN_READY
# }
# if KEEN_CREDENTIALS['keen_ready']:
#     KEEN_CREDENTIALS += {
#         'keen_project_id': osf_settings.KEEN_PROJECT_ID,
#         'keen_read_key': osf_settings.KEEN_READ_KEY,
#         'keen_write_key': osf_settings.KEEN_WRITE_KEY
#     }
