<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!from website import settings%>
    Hello ${user.fullname},
    <p>
    Your ${resource_type} <a href="${parent_url}">"${title}"</a> is in the process of being updated.
    <p>
    % if can_write:
        You can review and contribute to the updates by clicking <a href="${update_url}">here</a>.
    % else:
        You can review the updates by clicking <a href="${update_url}">here</a>.
    % endif
    <p>
    Sincerely yours,<br>
    The OSF Robots<br>
</tr>
</%def>
