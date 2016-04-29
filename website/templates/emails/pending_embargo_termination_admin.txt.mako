Hello ${user.fullname},

% if is_initiator:
You initiated a request to end the embargo for a registration of ${project_name}${context.get('custom_message', '')}. The embargoed registration can be viewed here: ${registration_link}.
% else:
${initiated_by} initiated a request to end the embargo for a registration of ${project_name}${context.get('custom_message', '')}. The embargoed registration can be viewed here: ${registration_link}.
% endif

To approve this change and to make this registration public immediately, click the following link: ${approval_link}.

To cancel this change, click the following link: ${disapproval_link}.

Sincerely yours,

The OSF Robots
