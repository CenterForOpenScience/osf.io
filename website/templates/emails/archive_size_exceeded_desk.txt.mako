<% from website import settings %>

User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (${src.url}), but the resulting archive would have exceeded our caps for disk usage (${settings.MAX_ARCHIVE_SIZE}MB).

A report is included below:

% for key in stat_result.targets:
<% result = stat_result.targets[key] %>
-------------------------
${result.target_name}:
  - Archive size: ${result.disk_usage}MB
  - Num. files: ${result.num_files}
  - Node settings pk: ${result.target_id}
% endfor 
