Hello${' {}'.format(user.fullname) if user else ''},

The email that you sent to ${target_address} was rejected, and was therefore not forwarded.

%if reason == mail_log_class.UNAUTHORIZED:
The reason for this rejection was that your email is not currently connected with an Open Science Framework account. If you have an account that you would like to connect with this email address, please visit [ http://osf.io/settings/account/ ] to do so.

%elif reason in (mail_log_class.DELETED, mail_log_class.NOT_FOUND, mail_log_class.FORBIDDEN):
The reason for this rejection was either that there is no project/component associated with the mailing list email that you sent to, or that you are not a contributor to the project/component associated with it.

%elif reason == mail_log_class.DISABLED:
The reason for this rejection was that your ${node_type} at ${node_url} does not have its mailing list currently enabled. Please ${'go to {}settings/#configureMailingListAnchor to enable this mailing list.'.format(node_url) if is_admin else 'ask an administrator on your {} to enable this mailing list.'.format(node_type)}

%elif reason == mail_log_class.NO_RECIPIENTS:
The reason for this rejection was that there are no contributors subscribed to this mailing list on your ${node_type} at ${node_url}

%endif

Sincerely,

Open Science Framework Robot

