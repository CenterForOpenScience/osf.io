<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    ID: ${user__id}<br>
    <br>
    Profile: ${user_absolute_url}<br>
    <br>
    Primary Email: ${user_username} <br>

</tr>
</%def>
