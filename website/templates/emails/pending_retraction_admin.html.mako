<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    % if is_initiator:
    You initiated a withdrawal of your registration ${project_name}. The registration can be viewed here: ${registration_link}.
    % else:
    ${initiated_by} initiated a withdrawal of your registration ${project_name}. The registration can be viewed here: ${registration_link}.
    % endif
    <p>
    % if is_moderated:
        If approved by project admins, a withdrawal request will be sent to ${reviewable.provider.name} moderators for review.
        <p>
        If the withdrawal request is accepted by ${reviewable.provider.name} moderators,  the registration will be
        marked as withdrawn. Its content will be removed from the OSF, but leave basic metadata behind.
        The title of a withdrawn registration and its contributor list will remain, as will justification or
        explanation of the withdrawal, should you wish to provide it.
    % else:
        If approved, the registration will be marked as withdrawn. Its content will be removed from the OSF, but leave basic
        metadata behind. The title of a withdrawn registration and its contributor list will remain, as will
        justification or explanation of the withdrawal, should you wish to provide it.
    % endif
    <p>
    To approve this withdrawal, click the following link: <a href="${approval_link}">Click here</a>.<br>
    To cancel this withdrawal, click the following link: <a href="${disapproval_link}">Click here</a>.
    <p>
    Note: Clicking the disapproval link will immediately cancel the pending withdrawal. This operation is irreversible.
    <p>
    % if is_moderated:
        If you neither approve nor cancel the withdrawal within ${approval_time_span} hours of midnight tonight (EDT)
         the withdrawal request will be sent to ${reviewable.provider.name} moderators for review.
    % else:
        If you neither approve nor cancel the withdrawal within ${approval_time_span} hours of midnight tonight (EDT)
         the registration will become withdrawn.
    % endif
	<p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
