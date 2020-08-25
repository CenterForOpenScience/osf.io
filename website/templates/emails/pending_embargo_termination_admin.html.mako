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
    To approve this change and to make this registration public immediately, click the following link: ${approval_link}.<br>
    <br>
    To cancel this change, click the following link: ${disapproval_link}.<br>
    <br>
    Note: Clicking the disapproval link will immediately cancel the embargo termination request. If you neither approve nor cancel the request within ${approval_time_span} hours from midnight tonight (EDT) the embargo will be lifted and the registration will be made public. This operation is irreversible.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The GRDM Robots<br>


</tr>
</%def>
