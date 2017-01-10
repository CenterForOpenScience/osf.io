import argparse
import logging

from framework.mongo import database
from framework.email import tasks
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website import settings
logger = logging.getLogger(__name__)

EMAILS_SENT_TO = {}  # Maps user.username: user._id
EMAIL_SUBJECT = 'Important information about your OSF Account'
EMAIL_TEMPLATE = \
u"""Hello {user_fullname},

This email is about your account on the Open Science Framework (OSF). For one or more of your projects you have connected figshare, Google Drive, Mendeley, or Box. 

Recently, we released an update that will require you to reauthorize any connections your account has to these add-ons. You can do this quickly by navigating to your account settings page, then the \"Configure Add-ons\" tab. Get there directly using this link: https://osf.io/settings/addons/ . From there, click \"connect or reauthorize your account.\" You will be redirected to the third party add-on site to authorize the connection. 

Until you reauthorize the connection between your account and these add-ons, the files stored there will not display correctly on the OSF.

We apologize for any inconvenience. Please don't hesitate to email support@osf.io with questions. 

Sincerely,

COS Product Team
"""

def send_mail(target, dry_run=True):
    """ Copied from `website/mails/mails.py`, updated to not 
        require `Mail` objects, to not require a template file.
    """
    to_addr = target['username']
    from_addr = settings.FROM_EMAIL
    mailer = tasks.send_email
    subject = EMAIL_SUBJECT
    message = EMAIL_TEMPLATE.format(user_fullname=target['fullname'])
    # Don't use ttls and login in DEBUG_MODE
    ttls = login = not settings.DEBUG_MODE
    logger.debug('Sending email From: {} To: {}:{}'.format(from_addr, target['_id'], to_addr))
    logger.debug(u'Message:\n{}'.format(message))

    kwargs = dict(
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        message=message,
        mimetype='plain',
        ttls=ttls,
        login=login,
        username=None,
        password=None,
        categories=None,
    )

    EMAILS_SENT_TO[to_addr] = target['_id']
    if settings.USE_EMAIL:
        if not dry_run:
            if settings.USE_CELERY:
                return mailer.apply_async(kwargs=kwargs)
            else:
                return mailer(**kwargs)

def any_account_is_connected_to_node_for_user(target):
    for account in target['external_accounts']:
        node_settings_model_name = settings.ADDONS_AVAILABLE_DICT[database.externalaccount.find_one(account, {'provider': 1})['provider']].settings_models['node']._name
        nids = [
            n['_id'] for n in database.node.find({'contributors': target['_id'], 'is_deleted': {'$ne': True}}, {'_id': 1}) 
            if database[node_settings_model_name].find({'owner': n['_id'], 'external_account': account}).count()
        ]
        if len(nids):
            return True
    return False

def get_targets():
    return [u for u in
        database.user.find({
            'external_accounts': {
                '$in': list(set(ea['_id'] for ea in \
                    list(database.externalaccount.find({'provider': {'$in': ['box', 'mendeley', 'googledrive']}, 'date_last_refreshed': None}, {'_id': 1})) + # Any Box/Mend/GD EA that hasn't been refreshed, OR
                    list(database.externalaccount.find({'provider': 'figshare'}, {'_id': 1}))))   # Any figshare EA
            },
            'merged_by': None,               # Not merged   (part of .is_active definition)
            'date_disabled': None,           # Not disabled (part of .is_active definition)
            'is_registered': True,           # Registered   (part of .is_active definition)
            'password': {'$ne': None},       # Has password (part of .is_active definition)
            'date_confirmed': {'$ne': None}  # Confirmed    (part of .is_active definition)
            }, {'_id': 1, 'external_accounts': 1, 'username': 1, 'fullname': 1})
        if any_account_is_connected_to_node_for_user(u)
    ]

def validate_target(target):
    assert target.get('username'), 'Found User {} with no username'.format(target['_id'])
    assert set([ea['provider'] for ea in database.externalaccount.find({'_id': {'$in': target['external_accounts']}})]) & set(['box', 'figshare', 'googledrive', 'mendeley']),\
        'Unable to determine target provider for accounts {}'.format(target['external_accounts'])
    assert target['username'] not in EMAILS_SENT_TO, 'Already emailed {}'.format(target['_id'])

def migrate(parsed_args):
    logger.info('Acquiring targets...')
    targets = get_targets()
    target_count = len(targets)
    count = 0

    logger.info('Preparing to migrate {} targets'.format(target_count))
    for target in targets:
        count += 1
        validate_target(target)
        logger.info('{}/{} Preparing to email User {}'.format(count, target_count, target['_id']))
        send_mail(target, parsed_args.dry_run)
        logger.info('{}/{} Successfully emailed User {} with external accounts {}'.format(count, target_count, target['_id'], target['external_accounts']))
    logger.info('Sent emails to users: {}'.format(list(EMAILS_SENT_TO.itervalues())))

def main():
    parser = argparse.ArgumentParser(
        description='Emails users with invalid credentials for Box, figshare, GoogleDrive, or Mendeley'
    )
    parser.add_argument(
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Run migration without sending emails and roll back any changes to database',
    )
    pargs = parser.parse_args()
    if not pargs.dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(pargs)
        if pargs.dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
