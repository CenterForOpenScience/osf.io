import Framework.Beaker as Session

def pushStatusMessage(message, level=0):
    statuses = Session.get('status')
    if not statuses:
        statuses = []
    statuses.append(message)
    Session.set('status', statuses)

def popStatusMessages(level=0):
    messages = Session.get('status')
    Session.set('status_prev', messages)
    Session.unset('status')
    return messages

def popPreviousStatusMessages(level=0):
    messages = Session.get('status_prev')
    Session.unset('status_prev')
    return messages
