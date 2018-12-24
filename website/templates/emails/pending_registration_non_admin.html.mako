<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    We just wanted to let you know that ${initiated_by} has initiated the following pending registration: ${registration_link}.<br>
    <br>
    If approved, a registration will be created for the project, viewable here: ${registration_link}, and it will remain<br>
    public until it is withdrawn.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robots<br>

</tr>
</%def>
