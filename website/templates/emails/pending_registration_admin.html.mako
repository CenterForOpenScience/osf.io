<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    % if is_initiator:
    You initiated a registration of your project ${project_name}. The proposed registration can be viewed here: ${registration_link}.<br>
    % else:
    ${initiated_by} has initiated a registration of your project ${project_name}. The proposed registration can be viewed here: ${registration_link}.<br>
    % endif
    <br>
    If approved, a registration will be created for the project and will be made public immediately.<br>
    <br>
    To approve this registration, click the following link: ${approval_link}<br>
    <br>
    To cancel this registration, click the following link: ${disapproval_link}<br>
    <br>
    Note: Clicking the disapproval link will immediately cancel the pending registration and the<br>
    registration will remain in draft state. If you neither approve nor cancel the registration<br>
    within ${approval_time_span} hours from midnight tonight (EDT) the registration will be<br>
    automatically approved and made public. This operation is irreversible.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>


</tr>
</%def>
