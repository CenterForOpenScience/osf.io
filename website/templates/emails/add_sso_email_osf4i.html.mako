<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">

    Hello ${user.fullname},<br>
    <br>
    Thank you for connecting to OSF through your institution. This email address has been added to your account as an alternate email address. If you would like to make this your primary contact address you can find instructions to do so at: <a href="https://help.osf.io/article/238-add-a-new-email-address-to-your-account#change-your-primary-email-address-on-your-account">https://help.osf.io/article/238-add-a-new-email-address-to-your-account#change-your-primary-email-address-on-your-account</a>.
    <br>
    If you have any issues, questions or need our help, contact support@osf.io and we will be happy to assist.
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>

</tr>
</%def>
