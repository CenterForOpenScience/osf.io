<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${fullname},<br>
    <br>
    You recently tried to create a project on the Open Science Framework via email, but your message did not contain any file attachments. Please try again, making sure to attach the files you'd like to upload to your message.<br>
    <br>

    Sincerely yours,<br>
    <br>
    The OSF Robot<br>

</tr>
</%def>
