<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${fullname},<br>
    <br>
    You have been added by ${referrer.fullname} as a contributor to the draft registration "${node.title}" on the OSF. To set a password for your account, visit:<br>
    <br>
    ${claim_url}<br>
    <br>
    Once you have set a password, you will be able to make contributions to "${node.title}" and create your own draft registrations and projects. You will automatically be subscribed to notification emails for this draft registration. To change your email notification preferences, visit your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    To preview "${node.title}" click the following link: ${node.absolute_url}<br>
    <br>
    If you are not ${fullname} or you are erroneously being associated with "${node.title}" then email ${osf_contact_email} with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    OSF Robot<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about the OSF, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>

</tr>
</%def>
