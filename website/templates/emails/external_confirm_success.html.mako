<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Congratulations! You have successfully linked your ${external_id_provider} account to the OSF (OSF).<br>
    <br>
    The OSF Team<br>


</tr>
</%def>
