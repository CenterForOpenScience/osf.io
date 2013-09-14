from framework import session

def push_status_message(message, level=0):
    statuses = session.get('status')
    if not statuses:
        statuses = []
    statuses.append(message)
    session['status'] = statuses

def pop_status_messages(level=0):
    messages = session.get('status')
    session['status_prev'] = messages
    if 'status' in session:
        del session['status']
    return messages

def pop_previous_status_messages(level=0):
    messages = session.get('status_prev')
    if 'status_prev' in session:
        del session['status_prev']
    return messages
