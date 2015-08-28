Hello ${user.fullname},

% if is_initiator:
You initiated a retraction of your registration ${project_name}. The registration can be viewed here: ${registration_link}.
% else:
${initiated_by} initiated a retraction of your registration ${project_name}. The registration can be viewed here: ${registration_link}.
% endif

If approved, the registration will be marked as retracted. Its content will be removed from the OSF, but leave basic metadata behind. The title of a retracted registration and its contributor list will remain, as will justification or explanation of the retraction, should you wish to provide it.

To approve this retraction, click the following link: ${approval_link}.

To cancel this retraction, click the following link: ${disapproval_link}.

Note: Clicking the disapproval link will immediately cancel the pending retraction. If you neither approve nor disapprove the retraction within ${approval_time_span} hours of midnight tonight (EDT) the registration will become retracted. This operation is irreversible.
Sincerely yours,

The OSF Robots
