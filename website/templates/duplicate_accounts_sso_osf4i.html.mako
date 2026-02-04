<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
    <td style="border-collapse: collapse;">
        Hello ${user_fullname},<br>
        <br>
        Thank you for connecting to OSF through your institution. We have found two OSF accounts associated with your institutional identity: &lt;${user_username}&gt;(${user__id}) and &lt;${duplicate_user_username}&gt;(${duplicate_user__id}). We have made &lt;${user_username}&gt; the account primarily associated with your institution.<br>
        <br>
        If &lt;${duplicate_user_username}&gt; is also your account, we would encourage you to merge it into your primary account. Instructions for merging your accounts can be found at: <a href="https://help.osf.io/article/237-merge-your-accounts">Merge Your Accounts</a>. This action will move all projects and components associated with &lt;${duplicate_user_username}&gt; into the &lt;${user_username}&gt; account.<br>
        <br>
        If you want to keep &lt;${duplicate_user_username}&gt; separate from &lt;${user_username}&gt; you will need to log into that account with your email and OSF password instead of the institutional authentication.<br>
        <br>
        If you have any issues, questions or need our help, contact <a href="mailto:${osf_support_email}">${osf_support_email}</a> and we will be happy to assist.<br>
        <br>
        Sincerely,<br>
        <br>
        The OSF Team<br>
    </td>
</tr>
</%def>
