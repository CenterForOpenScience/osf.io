<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},
    <p>
    % if is_initiator:
    You initiated a request to end the embargo for a registration of ${project_name}. The embargoed registration can be viewed here: ${registration_link}.
    % else:
    ${initiated_by} initiated a request to end the embargo for a registration of ${project_name}. The embargoed registration can be viewed here: ${registration_link}.
    % endif
    <p>
    Approve this change and make this registration public immediately:  <a href="${approval_link}">Click here</a>.<br>
    Cancel this change and keep embargo the same:  <a href="${disapproval_link}">Click here</a>
    <p>
    Note: Clicking the disapproval link will immediately cancel the embargo termination request. This operation is irreversible.
    <p>
    If you neither approve nor cancel the request within ${approval_time_span} hours from midnight tonight (EDT) the embargo will be lifted and the registration will be made public.
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
