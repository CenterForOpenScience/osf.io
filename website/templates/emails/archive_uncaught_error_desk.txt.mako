User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (${src.url}) [${src._id}], but the archive task failed unexpectedly.

A report is included below:

<% import json %>

% for error in results:
${error}
% endfor
