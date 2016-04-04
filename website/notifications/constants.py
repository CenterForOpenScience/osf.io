NODE_SUBSCRIPTIONS_AVAILABLE = {
    'comments': 'Comments added',
    'file_updated': 'Files updated',
    'mentions': 'Mentions added',
    'mentions_replies': 'Replies with mentions added'
}

USER_SUBSCRIPTIONS_AVAILABLE = {
    'comment_replies': 'Replies to your comments',
    'global_comments': 'Comments added',
    'global_file_updated': 'Files updated'
}

# Note: the python value None mean inherit from parent
NOTIFICATION_TYPES = {
    'email_transactional': 'Email when a change occurs',
    'email_digest': 'Daily email digest of all changes to this project',
    'none': 'None'
}

# Formatted file provider names for notification emails
PROVIDERS = {
    'osfstorage': 'OSF Storage',
    'box': 'Box',
    'dataverse': 'Dataverse',
    'dropbox': 'Dropbox',
    'figshare': 'figshare',
    'github': 'GitHub',
    'googledrive': 'Google Drive',
    's3': 'Amazon S3'
}
