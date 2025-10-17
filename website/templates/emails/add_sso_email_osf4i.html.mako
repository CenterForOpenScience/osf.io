<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
    <td style="border-collapse: collapse;">
        Hello ${user.fullname},<br>
        <br>
        Thank you for connecting to OSF through your institution. This email address &lt;${email_to_add}&gt; has been added to your account as an alternate email address.<br>
        <br>
        If you would like to make this your primary contact address you can find instructions to do so at: <a href="https://help.osf.io/article/238-add-a-new-email-address-to-your-account#change-your-primary-email-address-on-your-account">Change Your Primary Email Address On Your Account</a>.<br>
        <br>
        If you have any issues, questions or need our help, contact <a href="mailto:${osf_support_email}">${osf_support_email}</a> and we will be happy to assist.<br>
        <br>
        Sincerely,<br>
        <br>
        The OSF Team<br>
    </td>
</tr>
</%def>
