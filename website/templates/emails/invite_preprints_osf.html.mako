<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${fullname},<br>
    <br>
    You have been added by ${referrer.fullname} as a contributor to the preprint "${node.title}" on the Open Science Framework. To set a password for your account, visit:<br>
    <br>
    ${claim_url}<br>
    <br>
    Once you have set a password, you will be able to make contributions to "${node.title}" and create your own preprints and projects. You will automatically be subscribed to notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    To preview "${node.title}" click the following link: ${node.absolute_url}<br>
    <br>
    (NOTE: if this project is private, you will not be able to view it until you have confirmed your account)<br>
    <br>
    If you are not ${fullname} or you are erroneously being associated with "${node.title}" then email contact@osf.io with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    Open Science Framework Robot<br>
    <br>
    Center for Open Science<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email contact@osf.io<br>

</tr>
</%def>
