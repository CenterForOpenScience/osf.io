<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    % if is_initiator:
        You initiated an embargoed registration of ${project_name} with embargo end date ${embargo_end_date.date()}.
		The proposed registration can be viewed here: ${registration_link}.
    % else:
        ${initiated_by} initiated an embargoed registration of ${project_name} with embargo end date ${embargo_end_date.date()}.
		The proposed registration can be viewed here: ${registration_link}.
    % endif
    <p>
    % if is_moderated:
        If approved, an embargoed registration will be created for the project and sent to ${reviewable.provider.name}
         moderators for review.
    % else:
        If approved, a registration will be created for the project, and it will remain private until it is withdrawn,
         it is manually made public, or the embargo end date is passed on ${embargo_end_date.date()}.
    % endif
    <p>
    Approve this embargoed registration: <a href="${approval_link}">Click here</a>.<br>
    Cancel this embargoed registration: <a href="${disapproval_link}">Click here</a>.
    <p>
    Note: Clicking the cancel link will immediately cancel the pending embargo and the registration will remain in draft state. This operation is irreversible.
    <p>
    If you neither approve nor cancel the embargo within ${approval_time_span} hours from midnight tonight (EDT) the registration will
    % if is_moderated:
        enter into embargo automatically and be sent to ${reviewable.provider.name} moderators for review.
    % else:
     remain private and enter into an embargoed state.
    % endif
	<p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
