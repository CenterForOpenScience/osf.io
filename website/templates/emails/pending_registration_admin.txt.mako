Hello ${user.fullname},

% if is_initiator:
You initiated a registration of your project ${project_name}.
% else:
${initiated_by} has initiated a registration of your project ${project_name}.
% endif The pending registration can be viewed here: ${registration_link}.

To approve this registration, click the following link: ${approval_link}

To immediately cancel this registration, click the following link: ${disapproval_link}

Note: If you take no action within ${approval_time_span}, the registration will be automatically approved. This operation is irreversible.

Sincerely yours,

The OSF Robots
