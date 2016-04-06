<% from website import settings %>

User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (${src.url}), but the resulting archive would have exceeded our caps for disk usage (${settings.MAX_ARCHIVE_SIZE / 1024 ** 3}GB).

A report is included below:

${str(stat_result)}
