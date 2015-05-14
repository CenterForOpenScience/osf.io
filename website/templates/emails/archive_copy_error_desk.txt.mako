User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (${src.url}) [${src._id}], but the archive task failed.

A report is included below:

<% import json %>

% for addon in results:
<% result = results[addon] %>
${addon}: 
  - ${result['status']}
   % for err in result.get('errors', []):
     ${json.dumps(err)}
   % endfor
% endfor
