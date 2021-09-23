<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    Your Registration <a href="${response.parent.absolute_url}">{response.parent.title}</a>
    is in the process of being updated. You can view and contribute to the updates by clicking
    <a href="${response.osf_url}">here</a>
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
