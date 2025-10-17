<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},<br>
    <br>
    The password for your OSF account has successfully changed. <br>
    <br>
    If you did not request this action or you believe an unauthorized person has accessed your account, reset your password immediately by visiting:<br>
    <br>
	${settings.DOMAIN + "settings/account"}
    <br>
    If you need additional help or have questions, let us know at ${osf_contact_email}.<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robot<br>

</tr>
</%def>
