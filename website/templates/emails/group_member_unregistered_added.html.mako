<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has added you' if referrer_name else 'You have been added'} to the group "${group_name}" on OSF. To set a password for your account, visit:<br>
    <br>
    ${claim_url}<br>
    <br>
    Once you have set a password, you will be able to create your own groups and projects.
    <br>
    If you are not ${user.fullname} or you are erroneously being associated with "${group_name}," please email ${osf_contact_email} with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
    <br>
</tr>
</%def>
