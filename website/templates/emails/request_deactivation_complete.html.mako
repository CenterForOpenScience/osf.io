<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hi ${user.given_name},
    <br>
    <br>

    Your OSF account has been deactivated. You will not show up in search, nor will a profile be visible for you.
    If you try to log in, you will receive an error message that your account has been disabled. If, in the future,
    you would like to create an account with this email address, you can do so by emailing us at ${contact_email}.

    <br>
    <br>
    Sincerely,
    The OSF Team
</tr>
</%def>