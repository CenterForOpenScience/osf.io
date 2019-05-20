<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    Welcome to the GakuNin RDM and the Election Research Preacceptance Competition. To continue, please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    From the team at the National Institute of Informatics<br>

</tr>
</%def>
