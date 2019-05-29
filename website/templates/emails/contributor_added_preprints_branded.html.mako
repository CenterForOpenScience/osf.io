<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hello ${user.fullname},<br>
    <br>
    ${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the ${branded_service.preprint_word} "${node.title}" on ${branded_service.name}, which is hosted on the GakuNin RDM: ${node.absolute_url}<br>
    <br>
    You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this ${branded_service.preprint_word}. Each ${branded_service.preprint_word} is associated with a project on the GakuNin RDM for managing the ${branded_service.preprint_word}. To change your email notification preferences, visit your project user settings: ${settings.DOMAIN + "settings/notifications/"}<br>
    <br>
    If you have been erroneously associated with "${node.title}", then you may visit the project's "Contributors" page and remove yourself as a contributor.<br>
    <br>
    Sincerely,<br>
    <br>
    Your ${branded_service.name} and GRDM teams<br>
    <br>
    Want more information? Visit https://rdm.nii.ac.jp/preprints/${branded_service._id} to learn about ${branded_service.name} or https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.<br>
    <br>
    Questions? Email support+${branded_service._id}@osf.io<br>

</tr>
</%def>
