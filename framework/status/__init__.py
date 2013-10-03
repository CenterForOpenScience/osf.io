from framework import session

def push_status_message(message, level=0):
    statuses = session.data.get('status')
    if not statuses:
        statuses = []
    statuses.append(message)
    session.data['status'] = statuses

def pop_status_messages(level=0):
    messages = session.data.get('status')
    session.status_prev = messages
    if 'status' in session.data:
        del session.data['status']
    return messages

def pop_previous_status_messages(level=0):
    messages = session.data.get('status_prev')
    if 'status_prev' in session.data:
        del session.data['status_prev']
    return messages
