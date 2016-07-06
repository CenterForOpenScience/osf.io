
User: ${user.fullname} (${user.username}) [${user._id}]

Registration ${src.title} [${src._id}] is stuck in archiving.

Archive Job: [${archive_job._id}]

<% import json %>

${archive_job.to_storage()}

Automatically sent from scripts/cleanup_failed_registrations.py
