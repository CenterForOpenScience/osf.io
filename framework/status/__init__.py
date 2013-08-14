import framework.beaker as session

def push_status_message(message, level=0):
    statuses = session.get('status')
    if not statuses:
        statuses = []
    statuses.append(message)
    session.set('status', statuses)

def pop_status_messages(level=0):
    messages = session.get('status')
    session.set('status_prev', messages)
    session.unset('status')
    return messages

def pop_previous_status_messages(level=0):
    messages = session.get('status_prev')
    session.unset('status_prev')
    return messages
