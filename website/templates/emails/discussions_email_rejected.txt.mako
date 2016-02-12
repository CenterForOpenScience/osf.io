Hello${' {}'.format(user.fullname) if user else ''},

The email that you sent to ${target_address} was rejected, and was therefore not forwarded.

%if reason == 'no_user':
The reason for this rejection was that your email is not currently connected with an Open Science Framework account. If you have an account that you would like to connect with this email address, please visit [ http://osf.io/settings/account/ ] to do so.

%elif reason == 'node_deleted' or reason == 'node_dne' or reason == 'no_access':
The reason for this rejection was either that there is no project/component associated with the discussions email that you sent to, or that you are not a contributor to the project/component associated with it.

%elif reason == 'discussions_disabled':
The reason for this rejection was that your ${node_type} at ${node_url} does not have discussions currently enabled. Please ${'go to {}settings/#configureDiscussionsAnchor to enable email discussions.'.format(node_url) if is_admin else 'ask an administrator on your {} to enable email discussions.'.format(node_type)}

%endif

Sincerely,

Open Science Framework Robot

