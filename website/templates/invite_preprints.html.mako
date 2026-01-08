<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    You have been added by ${referrer_name} as a contributor to the ${branded_service_preprint_word}  <a href="${node_absolute_url}">${node_title}</a> on ${branded_service_name}, powered by the Open Science Framework.<br>
    <br>
    <a href="${claim_url}">Click here</a> to set a password for your account.<br>
    <br>
    Once you have set a password, you will be able to make contributions to <a href="${node_absolute_url}">${node_title}</a> and create your own ${branded_service_preprint_word}. You will automatically be subscribed to notification emails for this ${branded_service_preprint_word}. To change your email notification preferences, visit your user <a href="${domain + "settings/notifications/"}">settings</a><br>
    <br>
    (NOTE: if this preprint is unpublished, you will not be able to view it until you have confirmed your account)<br>
    <br>
    If you are not ${user_fullname} or you have been erroneously associated with <a href="${node_absolute_url}">${node_title}</a>, then email contact+${branded_service__id}@osf.io with the subject line "Claiming Error" to report the problem.<br>
    <br>
    Sincerely,<br>
    <br>
    Your ${branded_service_name} and OSF teams<br>
    <br>
    Want more information? Visit https://osf.io/preprints/${branded_service__id} to learn about ${branded_service_name} or https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.<br>
    <br>
    Questions? Email support+${branded_service__id}@osf.io<br>

</tr>
</%def>
