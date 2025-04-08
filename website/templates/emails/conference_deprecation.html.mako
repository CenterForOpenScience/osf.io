<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${fullname},<br>
    <br>
    You recently attempted to interact with the Meeting service via email, but this service has been discontinued and is no longer available for new interactions.<br>
    <br>
    Existing meetings and past submissions remain unchanged. If you have any questions or need further assistance, please contact our support team at [ ${support_email} ].<br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robot<br>
  </td>
</tr>
</%def>