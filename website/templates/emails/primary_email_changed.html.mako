<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    The primary email address for your OSF account has been changed to ${new_address}.<br>
    <br>
    If you did not request this action, let us know at contact@cos.io.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robot<br>

</tr>
</%def>
