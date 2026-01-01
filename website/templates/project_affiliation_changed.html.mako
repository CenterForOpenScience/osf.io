<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user_fullname},<br>
    <br>
    An Institutional admin has made changes to the affiliations of your project:
    <a href=${node_absolute_url}>${node_title}</a>.<br>
    <br>
    Want more information? Visit <a href="https://osf.io">OSF</a> to learn about OSF, or
    <a href="https://cos.io">COS</a> for information about its supporting organization,
    the Center for Open Science.<br>
    <br>
    Questions? Email <a href="mailto:contact@osf.io">contact@osf.io</a><br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robot<br>
  </td>
</tr>
</%def>
