<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    ${referrer_text} to the preprint <a href="${node_absolute_url}">${node_title}</a> on the Open Science Framework.<br>
    <br>
    If you are erroneously being associated with <a href="${node_absolute_url}">${node_title}</a>, then you may visit the preprint and remove yourself as a contributor.<br>
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
