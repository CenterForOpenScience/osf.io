<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    % if is_initiator:
    You initiated a request to end the embargo for a registration of ${project_name}. The embargoed registration can be viewed here: ${registration_link}.<br>
    % else:
    ${initiated_by} initiated a request to end the embargo for a registration of ${project_name}. The embargoed registration can be viewed here: ${registration_link}.<br>
    % endif
    <br>
    Approve this change and make this registration public immediately:  <a href="${approval_link}">Click here</a>.<br>
    <br>
    Cancel this change and keep embargo the same:  <a href="${disapproval_link}">Click here</a><br>
    <br>
    Note: Clicking the disapproval link will immediately cancel the embargo termination request. This operation is irreversible.
    <br>
    If you neither approve nor cancel the request within ${approval_time_span} hours from midnight tonight (EDT) the embargo will be lifted and the registration will be made public.
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>


</tr>
</%def>
