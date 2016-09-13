from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.mails import mails

@celery_app.task(ignore_results=True)
def on_node_updated(node_id, user_id, first_save, saved_fields, request_headers=None):
    from website.models import Node
    node = Node.load(node_id)

    if node.is_collection or node.archiving:
        return

    if request_headers:
        with TokuTransaction():
            # Will ban spammer
            node.check_spam(saved_fields, request_headers, mode='async', user_id=user_id, save=True)

    need_update = bool(node.SEARCH_UPDATE_FIELDS.intersection(saved_fields))
    # due to async nature of call this can issue a search delete for a new record (acceptable trade-off)
    if bool({'spam_status', 'is_deleted'}.intersection(saved_fields)):
        need_update = True
    elif not node.is_public and 'is_public' not in saved_fields:
        need_update = False
    if need_update:
        node.update_search()


@celery_app.task(ignore_results=True)
def on_user_suspension(user_id, system_tag):
    from framework.auth import User

    with TokuTransaction():
        user = User.load(user_id)
        if system_tag not in user.system_tags:
            user.system_tags.append(system_tag)
        if not user.is_disabled:
            user.disable_account()
            user.is_registered = False
            mails.send_mail(
                mail=mails.SPAM_USER_BANNED,
                user=user)
        user.save()
