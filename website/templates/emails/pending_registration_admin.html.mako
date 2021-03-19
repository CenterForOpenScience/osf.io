<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    % if is_initiator:
    You initiated a registration of your project ${project_name}. The proposed registration can be viewed here: ${registration_link}.
    % else:
    ${initiated_by} has initiated a registration of your project ${project_name}. The proposed registration can be viewed here: ${registration_link}.
    % endif
    <p>
    % if is_moderated:
         If approved, a registration will be created for the project and sent to ${reviewable.provider.name} moderators for review.
    % else:
        If approved, a registration will be created for the project and will be made public immediately.
    % endif
    <p>
    To approve this registration, click the following link: <a href="${approval_link}">Click here</a><br>
    To cancel this registration, click the following link: <a href="${disapproval_link}">Click here</a>
    <p>
    Note: Clicking the cancel link will immediately cancel the pending registration and the
    registration will remain in draft state. This operation is irreversible.
	<p>
    % if is_moderated:
        If you neither approve nor cancel the registration within ${approval_time_span} hours from
        midnight tonight (EDT) the registration will be automatically approved and
         sent to ${reviewable.provider.name} moderators for review.
    % else:
        If you neither approve nor cancel the registration within ${approval_time_span} hours from midnight tonight
         (EDT) the registration will be automatically approved and made public.
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
