<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your OSF login methods are changing</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello, ${user.fullname},<br>
    <br>
    Beginning today, login through your institution will no longer grant access to OSF.  <b>However, you will not lose access to your account or any of your OSF content.</b><br>
    <br>
    You can still access your account with an OSF password or with ORCID login.  Enabling multiple login methods will ensure that you maintain access to your OSF account even if you change your email address or other details.<br>
    <br>
    If you have already set an OSF password you are ready to log back into the OSF.  If you need to set an OSF password or if you are not sure if you have set one before, set a password here:<br>
    <br>
    <a href="${forgot_password_link}">${forgot_password_link}</a>,<br>
    <br>
    If you have issues setting a password for OSF, have issues logging in, or need help with your account, contact <a href="mailto:${osf_support_email}">${osf_support_email}</a>.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
  </td>
</tr>
</%def>
