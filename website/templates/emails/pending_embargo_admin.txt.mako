Hello ${user.fullname},

% if is_initiator:
You initiated an embargoed registration of ${project_name}${context.get('custom_message', '')}. The proposed registration can be viewed here: ${registration_link}.
% else:
${initiated_by} initiated an embargoed registration of ${project_name}${context.get('custom_message', '')}. The proposed registration can be viewed here: ${registration_link}.
% endif

If approved, a registration will be created for the project and it will remain private until it is retracted, manually
made public, or the embargo end date has passed on ${embargo_end_date.date()}.

To approve this embargo, click the following link: ${approval_link}.

To cancel this embargo, click the following link: ${disapproval_link}.

Note: Clicking the disapproval link will immediately cancel the pending embargo and the
registration will remain in draft state. If you neither approve nor disapprove the embargo
within ${approval_time_span} hours from midnight tonight (EDT) the registration will remain
private and enter into an embargoed state.

Sincerely yours,

The OSF Robots
