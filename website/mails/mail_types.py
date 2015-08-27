from datetime import datetime, timedelta

def _week_check(email):
    sent_emails = email.find_others_to()
    for email_ in sent_emails:
        if email_.sent_at > (datetime.utcnow() - timedelta(weeks=1)):
            return False
    return True

def no_addon(email):
    if _week_check(email):
        if len(email.to_.get_addons()) is 0:
            return True
    return False

def no_login(email):
    if _week_check(email):
        return True
    return False

email_types = {
    'no_addon': {
        'template': 'no_addon',
        'callback': no_addon,
    },
    'no_login': {
        'template': 'no_login',
        'callback': no_login,
    }
}
