<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your OSF login has changed - here's what you need to know!</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hello, ${user_fullname},<br>
    <br>
    Starting today, you can no longer sign into OSF using your institution's SSO. However, you will not lose access to your account or your OSF content.<br>
    <br>
    You can still access your OSF account using your institutional email by adding a password, or using your ORCID credentials (if your institutional email address is associated with your ORCID record).
      We also recommend having multiple ways to access your account by <a href="https://help.osf.io/hc/en-us/articles/360019737194-Sign-in-to-OSF#Sign-in-through-ORCID--">connecting your ORCID</a>
      or <a href="https://help.osf.io/hc/en-us/articles/360019738034-Add-a-New-Email-Address-to-Your-Account">alternate email addresses</a> with your account.<br>
    <br>
    Click <a href="${forgot_password_link}">here</a> to set a password<br>
    <br>
    If you have any issues, questions or need our help, contact <a href="mailto:${osf_support_email}">${osf_support_email}</a> and we will be happy to assist.
      You may find this <a href="https://help.osf.io/hc/en-us/articles/4403227058327-I-can-t-find-my-institution">help guide</a> useful.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
  </td>
</tr>
</%def>
