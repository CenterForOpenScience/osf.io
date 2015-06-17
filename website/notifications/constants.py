NODE_SUBSCRIPTIONS_AVAILABLE = {
    'comments': 'Comments Added',
    'wiki_updated': 'Wiki Updated',
    'file_updated': 'File updated'
}

USER_SUBSCRIPTIONS_AVAILABLE = {
    'comment_replies': 'Replies to your comments'
}

# Note: the python value None mean inherit from parent
NOTIFICATION_TYPES = {
    'email_transactional': 'Email when a change occurs',
    'email_quarter': 'Email at most 15 minutes after change occurs',
    'email_hour': 'Email on the hour about changes that have occurred',
    'email_digest': 'Daily email digest of all changes to this project',
    'none': 'None'
}

EMAIL_SUBJECT_MAP = {
    'comments': '${user.fullname} commented on "${title}".',
    'comment_replies': '${user.fullname} replied to your comment on "${title}".',
    'wiki_updated': '${user.fullname} updated the wiki on "${title}".',
    'file_updated': '${user.fullname} updated a file on "${title}".'
}
