from framework.celery_tasks import app
from website.settings import DATE_LAST_LOGIN_THROTTLE_DELTA


@app.task
def update_user_from_activity(user_id, login_time, cas_login=False, updates=None):
    from osf.models import OSFUser
    if not updates:
        updates = {}
    user = OSFUser.load(user_id)
    should_save = False
    if not user.date_last_login or user.date_last_login < login_time - DATE_LAST_LOGIN_THROTTLE_DELTA:
        user.update_date_last_login(login_time)
        should_save = True
    if cas_login:
        user.clean_email_verifications()
        user.update_affiliated_institutions_by_email_domain()
        if 'accepted_terms_of_service' in updates:
            user.accepted_terms_of_service = updates['accepted_terms_of_service']
        if 'verification_key' in updates:
            user.verification_key = updates['verification_key']
        should_save = True
    if should_save:
        user.save()
