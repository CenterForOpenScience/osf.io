<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Thank you for linking your ${external_id_provider} account to the Open Science Framework. We will add ${external_id_provider} to your OSF profile.<br>
    <br>
    Please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    The OSF Team<br>
    <br>
    Center for Open Science<br>


</tr>
</%def>
