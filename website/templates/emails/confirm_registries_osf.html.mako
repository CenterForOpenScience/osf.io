<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Welcome to the OSF and OSF Registries. To continue, please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    Sincerely,<br>
    <br>
    OSF Robot<br>

</tr>
</%def>
