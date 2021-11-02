from framework.celery_tasks import app

@app.task
def update_user_from_login(user_id, login_time, updates=None):
    from osf.models import OSFUser
    if not updates:
        updates = {}
    user = OSFUser.load(user_id)
    user.update_date_last_login(login_time)
    user.clean_email_verifications()
    user.update_affiliated_institutions_by_email_domain()
    if 'accepted_terms_of_service' in updates:
        user.accepted_terms_of_service = updates['accepted_terms_of_service']
    if 'verification_key' in updates:
        user.verification_key = updates['verification_key']
    user.save()
