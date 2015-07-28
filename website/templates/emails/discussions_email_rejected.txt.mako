Hello${' {}'.format(user.fullname) if user else ''},

The email that you sent to ${target_address} was rejcted, and was therefore not forwarded or recorded.

%if reason == 'no_user':
The reason for this rejection was that your email is not currently connected with an Open Science Framework account. If you have an account that you would like to connect with this email address, please visit [ http://osf.io/settings/account/ ] to do so.

%elif reason == 'project_deleted':
The reason for this rejection was that the ${node_type} that your email was sent to has already been deleted.

%elif reason == 'project_dne':
The reason for this rejection was either that there is no project/component associated with the discussions email that you sent to, or that project/component associated with it is private and you do not have access to it.

%elif reason == 'no_access':
The reason for this rejection was that you are not a contributor to the ${node_type} at ${node_url}. Please become a contributor if you would like to send email to this ${node_type}'s discussions list.

%elif reason == 'discussions_disabled':
The reason for this rejection was that your ${node_type} does not have discussions currently enabled. Please ${'go to {}settings/#configureDiscussionsAnchor to enable email discussions.'.format(node_url) if is_admin else 'ask an administrator on your project to enable email discussions.'}

%endif

Sincerely,

Open Science Framework Robot

