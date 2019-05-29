<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the ${branded_service.preprint_word} "${node.title}" on ${branded_service.name}, which is hosted on the Open Science Framework: ${node.absolute_url}<br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this ${branded_service.preprint_word}.  To change your email notification preferences, visit your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    If you have been erroneously associated with "${node.title}", then you may visit the ${branded_service.preprint_word} and remove yourself as a contributor.<br>
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
