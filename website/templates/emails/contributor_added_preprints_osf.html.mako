<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the preprint "${node.title}" on the Open Science Framework: ${node.absolute_url}<br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this preprint. To change your email notification preferences, visit your user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    If you are erroneously being associated with "${node.title}," then you may visit the preprint and remove yourself as a contributor.<br>
    <br>
    Sincerely,<br>
    <br>
    Open Science Framework Robot<br>
    <br>
    Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email ${osf_contact_email}<br>

</tr>
</%def>
