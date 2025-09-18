<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${fullname},<br>
    <br>
    You have been added by ${referrer.fullname} as a contributor to the ${branded_service.preprint_word} "${node.title}" on ${branded_service.name}, powered by the Open Science Framework. To set a password for your account, visit:<br>
    <br>
    ${claim_url}<br>
    <br>
    Once you have set a password, you will be able to make contributions to "${node.title}" and create your own ${branded_service.preprint_word}. You will automatically be subscribed to notification emails for this ${branded_service.preprint_word}. To change your email notification preferences, visit your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    To preview "${node.title}" click the following link: ${node.absolute_url}<br>
    <br>
    (NOTE: if this preprint is unpublished, you will not be able to view it until you have confirmed your account)<br>
    <br>
    If you are not ${fullname} or you have been erroneously associated with "${node.title}", then email contact+${branded_service._id}@osf.io with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    Your ${branded_service.name} and OSF teams<br>
    <br>
    Want more information? Visit https://osf.io/preprints/${branded_service._id} to learn about ${branded_service.name} or https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email support+${branded_service._id}@osf.io<br>

</tr>
</%def>
