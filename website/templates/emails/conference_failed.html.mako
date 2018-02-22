<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${fullname},<br>
    <br>
    Congratulations! You have successfully added your ${conf_full_name} ${presentation_type} to the Open Science Framework (OSF).<br>
    <br>

    Sincerely yours,<br>
    <br>
    The OSF Robot<br>
    <br>
    Center for Open Science<br>

</tr>
</%def>