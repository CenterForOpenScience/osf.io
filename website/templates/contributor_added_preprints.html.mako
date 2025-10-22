<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    ${referrer_text} to the ${branded_service_preprint_word} "${node_title}" on ${branded_service_name}, which is hosted on the Open Science Framework: ${node_absolute_url}<br>
    <br>
    If you have been erroneously associated with "${node_title}", then you may visit the ${branded_service_preprint_word} and remove yourself as a contributor.<br>
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
