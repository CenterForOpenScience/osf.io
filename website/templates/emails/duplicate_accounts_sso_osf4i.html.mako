<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">

    Hello ${user.fullname},<br>
    <br>
    Thank you for connecting to OSF through your institution. We have found two OSF accounts associated with your institutional identity: ${user.username} and ${duplicate_user.username}. We have made ${user.username} the account primarily associated with your institution. 
    <br>
    If ${duplicate_user.username} is also your account, we would encourage you to merge it into your primary account. Instructions for merging your accounts can be found at: <a href="https://help.osf.io/article/237-merge-your-accounts">https://help.osf.io/article/237-merge-your-accounts</a>. This action will move all projects and components associated with ${duplicate_user.username} into the ${user.username} account.
    <br>
    If you want to keep ${duplicate_user.username} separate from ${user.username} you will need to log into that account with your email and OSF password instead of the institutional authentication.
    <br>
    If you have any issues, questions or need our help, contact support@osf.io and we will be happy to assist. 
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>

</tr>
</%def>
