Hello ${user.fullname},

% if is_initiator:
You initiated a registration of your project ${project_name}${context.get('custom_message', '')}. The proposed registration can be viewed here: ${registration_link}.
% else:
${initiated_by} has initiated a registration of your project ${project_name}${context.get('custom_message', '')}. The proposed registration can be viewed here: ${registration_link}.
% endif

If approved, a registration will be created for the project and will be made public immediately.

To approve this registration, click the following link: ${approval_link}

To cancel this registration, click the following link: ${disapproval_link}

Note: Clicking the disapproval link will immediately cancel the pending embargo and the
registration will remain in draft state. If you neither approve nor cancel the registration
within ${approval_time_span} hours from midnight tonight (EDT) the registration will be
automatically approved and made public. This operation is irreversible.

Sincerely yours,

The OSF Robots
