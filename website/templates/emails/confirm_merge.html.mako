<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${merge_target.fullname},<br>
    <br>
    This email is to notify you that ${user.username} has an initiated an account merge with your account on the Open Science Framework (OSF). This merge will move all of the projects and components associated with ${email} and with ${user.username} into one account. All projects and components will be displayed under ${user.username}.<br>
    <br>
    Both ${user.username} and ${email} can be used to log into the account. However, ${email} will no longer show up in user search.<br>
    <br>
    This action is irreversible. To confirm this account merge, click this link: ${confirmation_url}.<br>
    <br>
    If you do not wish to merge these accounts, no action is required on your part. If you have any questions about this email, please direct them to ${osf_support_email}.<br>
    <br>
    Center for Open Science<br>

</tr>
</%def>