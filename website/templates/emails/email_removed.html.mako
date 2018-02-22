<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    The email address ${removed_email} has been removed from your account. For security purposes, a copy of this message has also been sent to your account's ${security_addr}.<br>
    <br>
    <br>
    If you did not request this action, let us know at contact@cos.io.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robot<br>
    <br>
    Center for Open Science<br>


</tr>
</%def>
