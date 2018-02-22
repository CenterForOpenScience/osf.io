<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Welcome to the Open Science Framework and OSF Preprints. To continue, please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    Sincerely yours,<br>
    <br>
    Open Science Framework Robot<br>
    <br>
    Center for Open Science<br>

</tr>
</%def>