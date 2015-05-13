User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (src.url), but the archive task failed.

A report is included below:

% for adddon in report:
<% result = report[addon] %>
-------------------------
${addon}: \n
  - status: ${result['status']}\n
  - errors:\n
  % for err in result['errors']:
    ${err}\n
  % endfor
% endfor
