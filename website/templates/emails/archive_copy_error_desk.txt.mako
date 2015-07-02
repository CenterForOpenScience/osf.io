User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (${src.url}) [${src._id}], but the archive task failed when copying files.

A report is included below:

<% import json %>

% for addon in results:
${addon['name']}:
  - ${addon['status']}
   % for err in addon['errors']:
     ${json.dumps(err)}
   % endfor
% endfor
