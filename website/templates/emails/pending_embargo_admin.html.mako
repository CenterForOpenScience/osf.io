<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    % if is_initiator:
    You initiated an embargoed registration of ${project_name}. The proposed registration can be viewed here: ${registration_link}.<br>
    % else:
    ${initiated_by} initiated an embargoed registration of ${project_name}. The proposed registration can be viewed here: ${registration_link}.<br>
    % endif
    <br>
    If approved, a registration will be created for the project and it will remain private until it is withdrawn, manually<br>
    made public, or the embargo end date has passed on ${embargo_end_date.date()}.<br>
    <br>
    To approve this embargo, click the following link: ${approval_link}.<br>
    <br>
    To cancel this embargo, click the following link: ${disapproval_link}.<br>
    <br>
    Note: Clicking the disapproval link will immediately cancel the pending embargo and the<br>
    registration will remain in draft state. If you neither approve nor disapprove the embargo<br>
    within ${approval_time_span} hours from midnight tonight (EDT) the registration will remain<br>
    private and enter into an embargoed state.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>


</tr>
</%def>
