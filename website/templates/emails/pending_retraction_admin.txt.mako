Hello ${user.fullname},

% if is_initiator:
You initiated a withdrawal of your registration ${project_name}. The registration can be viewed here: ${registration_link}.
% else:
${initiated_by} initiated a withdrawal of your registration ${project_name}. The registration can be viewed here: ${registration_link}.
% endif

If approved, the registration will be marked as withdrawn. Its content will be removed from the OSF, but leave basic metadata behind. The title of a withdrawn registration and its contributor list will remain, as will justification or explanation of the withdrawal, should you wish to provide it.

To approve this withdrawal, click the following link: ${approval_link}.

To cancel this withdrawal, click the following link: ${disapproval_link}.

Note: Clicking the disapproval link will immediately cancel the pending withdrawal. If you neither approve nor disapprove the withdrawal within ${approval_time_span} hours of midnight tonight (EDT) the registration will become withdrawn. This operation is irreversible.
Sincerely yours,

The OSF Robots
