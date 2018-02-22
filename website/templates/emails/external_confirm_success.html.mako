<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Congratulations! You have successfully linked your ${external_id_provider} account to the Open Science Framework (OSF).<br>
    <br>
    The OSF Team<br>
    <br>
    Center for Open Science<br>


</tr>
</%def>
